import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from functions.api.app import App
from shared.ai.gemini import GeminiClient, GeminiError
from shared.ai.guardrails import is_acceptable
from shared.briefing.selection import live, select_stories
from shared.repositories.memory import MemoryRepository
from tests.helpers import NOW, event, seed_pool, settings


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.pool = seed_pool(MemoryRepository()).query_pool("2026-11-13", 100)

    def counts(self, picks):
        out = {}
        for a in picks:
            out[a["category"]] = out.get(a["category"], 0) + 1
        return out

    def test_default_allocation_is_3_2_3_2(self):
        picks = select_stories(self.pool, set(), 10)
        # slots first, then leftovers go to the best remaining: totals stay 10
        self.assertEqual(len(picks), 10)
        c = self.counts(picks)
        self.assertGreaterEqual(c["technology"], 3)
        self.assertGreaterEqual(c["crypto"], 3)

    def test_muted_category_excluded_and_slots_reallocated(self):
        picks = select_stories(self.pool, {"government"}, 10)
        self.assertEqual(len(picks), 10)
        self.assertNotIn("government", self.counts(picks))

    def test_thin_category_slots_go_elsewhere_and_no_fabrication(self):
        thin = [a for a in self.pool if a["category"] != "stocks"] + [a for a in self.pool if a["category"] == "stocks"][:1]
        self.assertEqual(len(select_stories(thin, set(), 10)), 10)
        self.assertEqual(len(select_stories(self.pool[:4], set(), 10)), 4)

    def test_excludes_delivered_and_low_scores(self):
        first = select_stories(self.pool, set(), 10)
        second = select_stories(self.pool, set(), 10, exclude_ids=[a["id"] for a in first])
        self.assertFalse({a["id"] for a in first} & {a["id"] for a in second})
        self.assertEqual(select_stories(self.pool, set(), 10, min_score=0.99), [])

    def test_ttl_filter_excludes_expired_even_if_not_deleted(self):
        pool = list(self.pool)
        pool[0] = dict(pool[0], expiresAt=int(NOW.timestamp()) - 1)
        self.assertEqual(len(live(pool, int(NOW.timestamp()))), len(pool) - 1)


class GuardrailAndGeminiTests(unittest.TestCase):
    def test_guardrails(self):
        orig = "Apple Inc. raises $3.5 billion in 2026 bond sale"
        self.assertTrue(is_acceptable(orig, "Apple Inc. borrows $3.5 billion in 2026, because money is free-ish"))
        self.assertFalse(is_acceptable(orig, "Apple Inc. raises $4 billion in 2026 bond sale, lol"))   # number changed
        self.assertFalse(is_acceptable(orig, "Some tech giant borrows a lot of money, as one does"))   # names dropped
        self.assertFalse(is_acceptable(orig, orig))
        self.assertFalse(is_acceptable(orig, "x" * 300))

    def _client(self, responses):
        it = iter(responses)
        return GeminiClient("k", "m", 1, 100, 0.5, retries=2, post=lambda *a: next(it), sleep=lambda s: None)

    def test_retries_on_429_then_parses_and_filters(self):
        good = {"candidates": [{"content": {"parts": [{"text": json.dumps([
            {"id": "a", "headline": "Nvidia, unsurprisingly, sells 5 chips"},
            {"id": "b", "headline": "Totally unrelated"}])}]}}]}
        c = self._client([(429, {}), (200, good)])
        out = c.rewrite_batch([{"id": "a", "title": "Nvidia sells 5 chips"}, {"id": "b", "title": "Fed holds rates at 4%"}], "witty")
        self.assertEqual(list(out), ["a"])
        self.assertEqual(c.calls, 2)

    def test_failures_raise_gemini_error(self):
        with self.assertRaises(GeminiError):
            self._client([(500, {})] * 3).rewrite_batch([{"id": "a", "title": "T"}], "witty")
        with self.assertRaises(GeminiError):
            self._client([(200, {"candidates": []})]).rewrite_batch([{"id": "a", "title": "T"}], "witty")
        with self.assertRaises(GeminiError):
            GeminiClient("", "m", 1, 1, 0.5).rewrite_batch([{"id": "a", "title": "T"}], "witty")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = seed_pool(MemoryRepository())
        self.s = settings()
        self.gem = None
        self.app = App(self.repo, self.s, gemini_factory=lambda: self.gem, now_fn=lambda: NOW, pool_ttl=0)
        self.token = json.loads(self.app.handle(event("POST", "/api/session"))["body"])["token"]

    def call(self, method, path, body=None, **kw):
        r = self.app.handle(event(method, path, self.token, body, **kw))
        return r["statusCode"], json.loads(r["body"])

    def fm(self, key):
        return self.call("POST", "/api/news/fetch-more", headers={"idempotency-key": key})

    def test_auth_required_and_tampered_token_rejected(self):
        self.assertEqual(self.app.handle(event("GET", "/api/briefing/today"))["statusCode"], 401)
        bad = self.token[:-2] + "xx"
        self.assertEqual(self.app.handle(event("GET", "/api/briefing/today", bad))["statusCode"], 401)

    def test_session_creation_rate_limited_per_ip(self):
        codes = [self.app.handle(event("POST", "/api/session", ip="9.9.9.9"))["statusCode"] for _ in range(22)]
        self.assertEqual(codes.count(201), self.s.sessions_per_ip_daily)
        self.assertEqual(codes[-1], 429)

    def test_briefing_has_ten_and_mute_reallocates(self):
        _, b = self.call("GET", "/api/briefing/today")
        self.assertEqual(b["total"], 10)
        self.assertEqual(b["fetchMore"]["remaining"], 2)
        st, _ = self.call("POST", "/api/preferences", {"mutedCategories": ["government"], "humourMode": "witty"})
        self.assertEqual(st, 200)
        _, b = self.call("GET", "/api/briefing/today")
        self.assertEqual(b["total"], 10)
        self.assertNotIn("government", {a["category"] for a in b["articles"]})
        self.assertNotIn("government", b["activeCategories"])

    def test_preferences_validation(self):
        self.assertEqual(self.call("POST", "/api/preferences", {"mutedCategories": ["sports"]})[0], 400)
        self.assertEqual(self.call("POST", "/api/preferences", {"mutedCategories": ["crypto", "stocks", "government", "technology"]})[0], 400)
        self.assertEqual(self.call("POST", "/api/preferences", {"humourMode": "evil"})[0], 400)
        self.assertEqual(self.app.handle(event("POST", "/api/preferences", self.token) | {"body": "{nope"})["statusCode"], 400)

    def test_fetch_more_two_batches_then_blocked_and_unique(self):
        _, b = self.call("GET", "/api/briefing/today")
        seen = {a["id"] for a in b["articles"]}
        for key, remaining in (("key-00000001", 1), ("key-00000002", 0)):
            st, r = self.fm(key)
            self.assertEqual((st, len(r["articles"]), r["fetchMore"]["remaining"]), (200, 10, remaining))
            ids = {a["id"] for a in r["articles"]}
            self.assertFalse(ids & seen)
            seen |= ids
        st, r = self.fm("key-00000003")
        self.assertEqual((st, r["error"]["code"]), (429, "FETCH_MORE_LIMIT_REACHED"))
        _, b = self.call("GET", "/api/briefing/today")
        self.assertEqual((b["total"], b["fetchMore"]["exhausted"], b["fetchMore"]["canFetchMore"]), (30, True, False))

    def test_fetch_more_idempotent_replay_does_not_consume_quota(self):
        st, first = self.fm("retry-key-0001")
        st2, again = self.fm("retry-key-0001")
        self.assertTrue(again["replayed"])
        self.assertEqual([a["id"] for a in first["articles"]], [a["id"] for a in again["articles"]])
        self.assertEqual(again["fetchMore"]["used"], 1)

    def test_fetch_more_requires_valid_key(self):
        self.assertEqual(self.call("POST", "/api/news/fetch-more")[0], 400)

    def test_concurrent_fetch_more_cannot_exceed_quota(self):
        self.call("GET", "/api/briefing/today")
        with ThreadPoolExecutor(12) as ex:
            results = list(ex.map(lambda i: self.fm(f"concurrent-{i:04d}"), range(12)))
        ok = [r for st, r in results if st == 200]
        self.assertEqual(len(ok), 2)
        usage = self.repo.get_usage(self.token.split(".")[1], "2026-11-13")
        self.assertEqual(usage["fetchMoreCount"], 2)
        self.assertEqual(len(usage["delivered"]), len(set(usage["delivered"])))  # never duplicated
        self.assertEqual(len(usage["delivered"]), 30)

    def test_empty_reserve_does_not_burn_quota(self):
        repo = seed_pool(MemoryRepository(), n=6)
        app = App(repo, self.s, now_fn=lambda: NOW, pool_ttl=0)
        tok = json.loads(app.handle(event("POST", "/api/session"))["body"])["token"]
        r = app.handle(event("POST", "/api/news/fetch-more", tok, headers={"idempotency-key": "empty-0001"}))
        body = json.loads(r["body"])
        self.assertEqual((r["statusCode"], body["articles"], body["fetchMore"]["used"]), (200, [], 0))
        _, b = (0, json.loads(app.handle(event("GET", "/api/briefing/today", tok))["body"]))
        self.assertEqual(b["total"], 6)
        self.assertIn("never pad", b["notice"])

    def test_rewrite_flow_cache_quota_and_failure_fallback(self):
        _, b = self.call("GET", "/api/briefing/today")
        art = b["articles"][0]
        self.assertIsNone(art["aiHeadline"])  # feed works without any AI rewrite
        self.gem = None
        self.assertEqual(self.call("POST", f"/api/news/{art['id']}/rewrite", {"mode": "roast"})[0], 503)

        class G:
            def rewrite_batch(_, items, mode):
                return {items[0]["id"]: f"{items[0]['title']}, but {mode}"}
        self.gem = G()
        st, r = self.call("POST", f"/api/news/{art['id']}/rewrite", {"mode": "roast"})
        self.assertEqual((st, r["cached"]), (200, False))
        self.assertTrue(self.call("POST", f"/api/news/{art['id']}/rewrite", {"mode": "roast"})[1]["cached"])
        self.assertEqual(self.call("POST", "/api/preferences", {"humourMode": "roast"})[0], 200)
        _, b = self.call("GET", "/api/briefing/today")
        self.assertEqual(b["articles"][0]["aiMode"], "roast")
        self.assertEqual(self.call("POST", "/api/news/" + "0" * 16 + "/rewrite", {})[0], 404)  # not delivered to user
        self.assertEqual(self.call("POST", "/api/news/bad-id/rewrite", {})[0], 404)

    def test_rewrite_user_quota(self):
        s = settings(rewrite_user_daily_limit=1)
        app = App(self.repo, s, gemini_factory=lambda: type("G", (), {"rewrite_batch": lambda _, i, m: {x["id"]: x["title"] + "!" for x in i}})(),
                  now_fn=lambda: NOW, pool_ttl=0)
        tok = json.loads(app.handle(event("POST", "/api/session"))["body"])["token"]
        b = json.loads(app.handle(event("GET", "/api/briefing/today", tok))["body"])
        codes = [app.handle(event("POST", f"/api/news/{a['id']}/rewrite", tok, {"mode": "genz"}))["statusCode"] for a in b["articles"][:3]]
        self.assertEqual(codes, [200, 429, 429])

    def test_news_listing_only_delivered_and_paginated(self):
        self.call("GET", "/api/briefing/today")
        _, r = self.call("GET", "/api/news", query={"limit": "4", "offset": "0"})
        self.assertEqual((len(r["articles"]), r["total"], r["nextOffset"]), (4, 10, 4))
        self.assertEqual(self.call("GET", "/api/news", query={"category": "sports"})[0], 400)

    def test_health_unknown_route_and_error_shape(self):
        r = self.app.handle(event("GET", "/api/health"))
        self.assertEqual(r["statusCode"], 200)
        st, body = self.call("GET", "/api/nope")
        self.assertEqual((st, body["error"]["code"]), (404, "NOT_FOUND"))

    def test_summary_endpoint(self):
        _, b = self.call("GET", "/api/briefing/today")
        aid = b["articles"][0]["id"]
        st, res = self.call("GET", f"/api/news/{aid}/summary")
        self.assertEqual(st, 200)
        self.assertIn("overview", res)
        self.assertIn("keyPoints", res)
        self.assertEqual(self.call("GET", "/api/news/0000000000000000/summary")[0], 404)

    def test_expired_article_not_served(self):
        later = NOW + timedelta(days=8)
        app = App(self.repo, self.s, now_fn=lambda: later, pool_ttl=0)
        tok = json.loads(app.handle(event("POST", "/api/session"))["body"])["token"]
        r = json.loads(app.handle(event("GET", "/api/briefing/today", tok))["body"])
        self.assertEqual(r["total"], 0)


if __name__ == "__main__":
    unittest.main()
