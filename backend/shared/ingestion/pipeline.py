"""Ingestion pipeline: fetch -> parse -> normalise -> dedupe -> rank -> persist. Independent of user traffic."""
from concurrent.futures import ThreadPoolExecutor

from ..ai.headlines import generate_default_rewrites
from ..briefing.selection import live
from ..utils import briefing_day, iso, log, previous_day
from .dedupe import find_duplicate, title_tokens
from .fetcher import FetchError, fetch_feed
from .ranking import score_article
from .rss import FeedParseError, parse_feed


def _process_feed(feed, repo, settings, now, fetch):
    """Returns (articles, health). Any failure is contained here so one bad source cannot stop the run."""
    state = (repo.get_many(["S#" + feed["id"]]) or [{}])[0]
    try:
        res = fetch(feed, state, settings.feed_timeout, settings.feed_retries)
        articles = [] if res["status"] == "not_modified" else parse_feed(
            res["body"], feed, now, settings.max_article_age_hours)
        health = {"lastSuccess": iso(now), "consecutiveFailures": 0, "lastError": None,
                  "lastCount": len(articles), "etag": res.get("etag"), "lastModified": res.get("lastModified"),
                  "status": res["status"]}
        return articles, health
    except (FetchError, FeedParseError) as exc:
        log("error", "feed_failed", feed=feed["id"], error=str(exc))
        return [], {**{k: state.get(k) for k in ("lastSuccess", "etag", "lastModified")},
                    "consecutiveFailures": int(state.get("consecutiveFailures", 0)) + 1,
                    "lastError": str(exc)[:200], "lastCount": 0, "status": "error"}


def run_ingestion(repo, feeds, settings, now, fetch=fetch_feed, gemini=None, og_fetch=None):
    day = briefing_day(now, settings.timezone)
    now_ts = int(now.timestamp())
    expires = now_ts + settings.retention_days * 86400

    with ThreadPoolExecutor(max_workers=settings.ingest_workers) as pool:  # bounded concurrency
        results = list(pool.map(lambda f: _process_feed(f, repo, settings, now, fetch), feeds))

    # Existing pool (today + yesterday) so cross-run duplicates are merged, not re-added.
    existing = {a["id"]: a for d in (day, previous_day(day))
                for a in live(repo.query_pool(d, settings.pool_limit), now_ts)}
    tokens = {i: title_tokens(a["title"]) for i, a in existing.items()}
    dirty, new_ids = set(), []

    candidates = sorted((a for arts, _ in results for a in arts), key=lambda a: -a["credibility"])
    for art in candidates:
        if art["id"] in existing:
            continue
        match = find_duplicate(title_tokens(art["title"]), tokens.items())
        if match:
            m = existing[match]
            if art.get("publisher") != m.get("publisher") and art.get("publisher") not in m.get("alsoReportedBy", []):
                m["alsoReportedBy"] = (m.get("alsoReportedBy", []) + [art.get("publisher", "")])[:8]
                m["coverage"] = 1 + len(m["alsoReportedBy"])
                dirty.add(match)
            if not m.get("image") and art.get("image"):  # a duplicate may carry the better image
                m["image"] = art["image"]
                dirty.add(match)
            if not m.get("summary") and art.get("summary"):
                m["summary"] = art["summary"]
                dirty.add(match)
            continue
        art.update(day=day, expiresAt=expires, firstSeenAt=iso(now), score=0.0)
        existing[art["id"]] = art
        tokens[art["id"]] = title_tokens(art["title"])
        new_ids.append(art["id"])

    written = 0
    for aid in new_ids:
        art = existing[aid]
        art["score"] = score_article(art, now)
        written += bool(repo.put_article(art))  # conditional put: idempotent under retries/overlap
    for aid, art in existing.items():
        if aid in new_ids or (art.get("day") != day and aid not in dirty):
            continue
        new_score = score_article(art, now)
        if aid in dirty or abs(new_score - art.get("score", 0)) > 0.005:
            art["score"] = new_score
            fields = {"score": new_score}
            if "coverage" in art:
                fields["coverage"] = art["coverage"]
            if "alsoReportedBy" in art:
                fields["alsoReportedBy"] = art["alsoReportedBy"]
            if art.get("image") is not None:
                fields["image"] = art["image"]
            if art.get("summary") is not None:
                fields["summary"] = art["summary"]
            repo.update_article(aid, fields)

    if og_fetch and settings.enable_og_fetch:
        _enrich_images(repo, existing, day, settings, og_fetch)

    for feed, (_, health) in zip(feeds, results):
        repo.put_meta("S#" + feed["id"], {**health, "feedId": feed["id"]})
    repo.put_meta("M#last_ingest", {"at": iso(now), "ingestDay": day, "new": len(new_ids),
                                    "sourcesOk": sum(1 for _, h in results if h["status"] != "error"),
                                    "sources": len(feeds)})

    ai = {"generated": 0, "geminiCalls": 0}
    if gemini:
        top = sorted((a for a in existing.values() if a.get("day") == day), key=lambda a: -a["score"])
        ai = generate_default_rewrites(repo, gemini, top[: settings.rewrite_top_n], settings, now)
    summary = {"day": day, "newArticles": written, "merged": len(dirty), **ai,
               "failedSources": [f["id"] for f, (_, h) in zip(feeds, results) if h["status"] == "error"]}
    log("info", "ingestion_done", **summary)
    return summary


def _enrich_images(repo, existing, day, settings, og_fetch):
    """Open Graph lookup for top direct-publisher stories without an RSS image (opt-in, bounded)."""
    budget = settings.og_fetch_per_run
    for a in sorted(existing.values(), key=lambda a: -a.get("score", 0)):
        if budget <= 0:
            break
        if a.get("day") != day or a.get("image") or "news.google.com" in a["url"]:
            continue
        budget -= 1
        try:
            url = og_fetch(a["url"])
        except Exception as exc:  # network/robots/SSRF guard failures are all non-fatal
            log("info", "og_skipped", articleId=a["id"], error=str(exc)[:100])
            continue
        if url:
            a["image"] = {"url": url, "source": "open_graph", "attribution": f"Image: {a.get('publisher', '')}",
                          "status": "unverified"}
            repo.update_article(a["id"], {"image": a["image"]})
