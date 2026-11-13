"""Headline rewrite orchestration: cache first, then budget, then Gemini. Never raises into callers
that render the feed - a failure simply means the original headline is shown."""
import time

from ..utils import briefing_day, log, utcnow
from .gemini import GeminiError
from .personalities import DEFAULT_MODE


def rewrite_key(article_id, mode):
    return f"R#{article_id}#{mode}"


def cached_rewrites(repo, article_ids, mode, now_ts):
    rows = repo.get_many([rewrite_key(i, mode) for i in article_ids])
    return {r["articleId"]: r["headline"] for r in rows if int(r.get("expiresAt", 0)) > now_ts}


def take_global_budget(repo, settings, now):
    """One Gemini HTTP request costs one unit of the shared daily budget."""
    day = briefing_day(now, settings.timezone)
    return repo.take_quota("Q#gemini", day, settings.gemini_daily_call_cap, 1, int(now.timestamp()) + 3 * 86400)


def generate_default_rewrites(repo, client, articles, settings, now=None):
    """Batch-generate default-mode rewrites for articles that have none yet (called by ingestion)."""
    now = now or utcnow()
    now_ts = int(now.timestamp())
    have = cached_rewrites(repo, [a["id"] for a in articles], DEFAULT_MODE, now_ts)
    todo = [a for a in articles if a["id"] not in have][: settings.rewrite_top_n]
    generated, calls = 0, 0
    for i in range(0, len(todo), settings.rewrite_batch_size):
        if calls >= settings.gemini_calls_per_run or not take_global_budget(repo, settings, now):
            log("warning", "gemini_budget_stop", calls=calls)
            break
        calls += 1
        batch = todo[i:i + settings.rewrite_batch_size]
        try:
            result = client.rewrite_batch(batch, DEFAULT_MODE)
        except GeminiError as exc:
            log("error", "gemini_failed", error=str(exc))
            break  # fail fast: the feed keeps working with original headlines
        for a in batch:
            if a["id"] in result and repo.put_rewrite(a["id"], DEFAULT_MODE, result[a["id"]],
                                                      now_ts + settings.retention_days * 86400):
                generated += 1
    return {"generated": generated, "geminiCalls": calls}
