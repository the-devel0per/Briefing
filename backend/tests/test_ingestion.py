import unittest
import urllib.error
from datetime import timedelta

from shared.ingestion.dedupe import find_duplicate, title_tokens
from shared.ingestion.fetcher import FetchError, fetch_feed
from shared.ingestion.pipeline import run_ingestion
from shared.ingestion.ranking import score_article
from shared.ingestion.rss import FeedParseError, canonical_url, parse_date, parse_feed
from shared.repositories.memory import MemoryRepository
from tests.helpers import NOW, rss, settings

GOOGLE = {"id": "gn-tech", "type": "google", "category": "technology", "url": "https://news.google.com/rss/x"}
DIRECT = {"id": "bbc", "type": "direct", "category": "technology", "publisher": "BBC News", "url": "https://bbc.co.uk/rss"}


class ParsingTests(unittest.TestCase):
    def test_google_item_strips_publisher_and_has_no_summary(self):
        xml = rss([("Nvidia unveils chip - Reuters", "https://news.google.com/a?utm_source=x", NOW,
                    "<source url='https://reuters.com'>Reuters</source><description>junk</description>")])
        [a] = parse_feed(xml, GOOGLE, NOW, 30)
        self.assertEqual((a["title"], a["publisher"], a["summary"]), ("Nvidia unveils chip", "Reuters", None))
        self.assertNotIn("utm_source", a["url"])

    def test_direct_feed_extracts_largest_https_image_and_summary(self):
        extra = ('<media:thumbnail url="https://i.bbc/small.jpg" width="100"/>'
                 '<media:thumbnail url="https://i.bbc/big.jpg" width="976"/>'
                 '<description>&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;</description>')
        [a] = parse_feed(rss([("AI model released", "https://bbc.co.uk/1", NOW, extra)]), DIRECT, NOW, 30)
        self.assertEqual(a["image"]["url"], "https://i.bbc/big.jpg")
        self.assertEqual(a["summary"], "Hello world")

    def test_http_images_are_rejected(self):
        extra = '<media:thumbnail url="http://insecure/x.jpg"/>'
        [a] = parse_feed(rss([("AI model released", "https://bbc.co.uk/1", NOW, extra)]), DIRECT, NOW, 30)
        self.assertIsNone(a["image"])

    def test_invalid_items_dropped_not_fatal(self):
        xml = (b'<rss><channel><item><title>No date</title><link>https://a.com/1</link></item>'
               b'<item><title>Bad date</title><link>https://a.com/2</link><pubDate>garbage</pubDate></item>'
               b'<item><title></title><link>https://a.com/3</link></item></channel></rss>')
        self.assertEqual(parse_feed(xml, DIRECT, NOW, 30), [])

    def test_old_and_future_items_rejected(self):
        xml = rss([("Old story here", "https://a.com/1", NOW - timedelta(hours=40), ""),
                   ("Future story here", "https://a.com/2", NOW + timedelta(days=2), ""),
                   ("Fresh story here", "https://a.com/3", NOW - timedelta(hours=2), "")])
        self.assertEqual([a["title"] for a in parse_feed(xml, DIRECT, NOW, 30)], ["Fresh story here"])

    def test_malicious_or_invalid_xml_raises(self):
        with self.assertRaises(FeedParseError):
            parse_feed(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><rss></rss>', DIRECT, NOW, 30)
        with self.assertRaises(FeedParseError):
            parse_feed(b"<rss><channel>", DIRECT, NOW, 30)

    def test_date_normalisation(self):
        self.assertEqual(parse_date("Fri, 13 Nov 2026 10:00:00 +0530").hour, 4)
        self.assertEqual(parse_date("2026-11-13T09:00:00Z").hour, 9)
        self.assertIsNone(parse_date("nope"))

    def test_canonical_url_drops_tracking(self):
        self.assertEqual(canonical_url("https://A.com/x?id=1&utm_campaign=z#frag"), "https://a.com/x?id=1")


class DedupeRankingTests(unittest.TestCase):
    def test_same_event_different_wording_is_duplicate(self):
        a = title_tokens("Nvidia unveils new AI chip for data centers")
        b = title_tokens("Nvidia unveils AI chip aimed at data centers")
        c = title_tokens("Fed holds interest rates steady")
        self.assertEqual(find_duplicate(a, [("b", b), ("c", c)]), "b")
        self.assertIsNone(find_duplicate(c, [("b", b)]))

    def test_ranking_prefers_fresh_credible_widely_covered(self):
        base = {"title": "Company announces plan", "publishedAt": "2026-11-13T08:00:00Z", "credibility": 0.5,
                "coverage": 1, "relevance": 0.5}
        strong = dict(base, credibility=0.95, coverage=5, title="Company acquires rival in billion deal")
        old = dict(base, publishedAt="2026-11-12T00:00:00Z")
        self.assertGreater(score_article(strong, NOW), score_article(base, NOW))
        self.assertGreater(score_article(base, NOW), score_article(old, NOW))


class FetcherTests(unittest.TestCase):
    def test_retries_then_succeeds(self):
        calls = {"n": 0}

        class Resp:
            headers = {"ETag": "e1"}
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self, n): return b"<rss/>"

        def opener(req, timeout):
            calls["n"] += 1
            if calls["n"] < 3:
                raise urllib.error.URLError("boom")
            return Resp()
        res = fetch_feed(DIRECT, {}, 1, 3, opener=opener, sleep=lambda s: None)
        self.assertEqual((res["status"], res["etag"], calls["n"]), ("ok", "e1", 3))

    def test_permanent_error_not_retried_and_non_https_blocked(self):
        calls = {"n": 0}

        def opener(req, timeout):
            calls["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)
        with self.assertRaises(FetchError):
            fetch_feed(DIRECT, {}, 1, 3, opener=opener, sleep=lambda s: None)
        self.assertEqual(calls["n"], 1)
        with self.assertRaises(FetchError):
            fetch_feed({**DIRECT, "url": "http://x.com/rss"}, {}, 1, 3)


class FakeGemini:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, 0

    def rewrite_batch(self, items, mode):
        from shared.ai.gemini import GeminiError
        self.calls += 1
        if self.fail:
            raise GeminiError("down")
        return {i["id"]: f"Wow: {i['title']} (again)" for i in items}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.s = settings(ingest_workers=2)
        self.repo = MemoryRepository()
        xml_a = rss([("Nvidia unveils new AI chip for data centers", "https://bbc.co.uk/1", NOW, ""),
                     ("Government passes sweeping AI regulation bill", "https://bbc.co.uk/2", NOW, "")])
        xml_b = rss([("Nvidia unveils AI chip aimed at data centers - Reuters", "https://news.google.com/z", NOW,
                      "<source url='https://reuters.com'>Reuters</source>")])
        self.pages = {"bbc": xml_a, "gn-tech": xml_b}

    def fetch(self, feed, state, timeout, retries):
        if feed["id"] == "broken":
            raise FetchError("HTTP 500")
        return {"status": "ok", "body": self.pages[feed["id"]], "etag": None, "lastModified": None}

    def test_end_to_end_with_failing_source_and_dedupe(self):
        feeds = [DIRECT, GOOGLE, {**DIRECT, "id": "broken"}]
        out = run_ingestion(self.repo, feeds, self.s, NOW, fetch=self.fetch, gemini=FakeGemini())
        self.assertEqual(out["failedSources"], ["broken"])
        self.assertEqual(out["newArticles"], 2)  # the Reuters copy merged into the BBC story
        pool = self.repo.query_pool("2026-11-13", 50)
        chip = next(a for a in pool if "chip" in a["title"])
        self.assertEqual((chip["coverage"], chip["alsoReportedBy"]), (2, ["BBC News"]))
        self.assertEqual(self.repo.get_many(["S#broken"])[0]["consecutiveFailures"], 1)
        self.assertEqual(self.repo.get_many(["S#bbc"])[0]["status"], "ok")
        self.assertEqual(out["generated"], 2)

    def test_idempotent_second_run_and_gemini_failure_is_contained(self):
        feeds = [DIRECT, GOOGLE]
        run_ingestion(self.repo, feeds, self.s, NOW, fetch=self.fetch, gemini=FakeGemini(fail=True))
        again = run_ingestion(self.repo, feeds, self.s, NOW, fetch=self.fetch, gemini=FakeGemini(fail=True))
        self.assertEqual(again["newArticles"], 0)
        self.assertEqual(len(self.repo.query_pool("2026-11-13", 50)), 2)

    def test_gemini_daily_budget_is_enforced(self):
        s = settings(gemini_daily_call_cap=1, rewrite_batch_size=1, gemini_calls_per_run=5)
        g = FakeGemini()
        run_ingestion(self.repo, [DIRECT], s, NOW, fetch=self.fetch, gemini=g)
        self.assertEqual(g.calls, 1)


if __name__ == "__main__":
    unittest.main()
