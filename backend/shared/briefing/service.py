"""Briefing use-cases: today's briefing, Fetch More, delivered-news listing and on-demand rewrites."""
import time

from ..ai.gemini import GeminiError
from ..ai.headlines import cached_rewrites, take_global_budget
from ..ai.personalities import DEFAULT_MODE, MODES
from ..config.categories import CATEGORIES
from ..utils import briefing_day, log, utcnow
from .selection import category_counts, live, select_stories

DEFAULT_PREFS = {"mutedCategories": [], "humourMode": DEFAULT_MODE}


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code = status, code


class BriefingService:
    def __init__(self, repo, settings, gemini_factory=None, pool_ttl=60):
        self.repo, self.s, self._gemini_factory = repo, settings, gemini_factory
        self._pool_ttl, self._pool_cache = pool_ttl, {}

    # ---- helpers ---------------------------------------------------------
    def _pool(self, day, now_ts):
        hit = self._pool_cache.get(day)
        if hit and hit[0] > time.monotonic():
            return live(hit[1], now_ts)
        rows = self.repo.query_pool(day, self.s.pool_limit)
        if rows:
            self._pool_cache[day] = (time.monotonic() + self._pool_ttl, rows)
        return live(rows, now_ts)

    def _prefs(self, uid):
        return {**DEFAULT_PREFS, **(self.repo.get_prefs(uid) or {})}

    def _usage_expiry(self, now):
        return int(now.timestamp()) + 3 * 86400

    def _resolve(self, ids, pool, now_ts):
        by_id = {a["id"]: a for a in pool}
        missing = [i for i in ids if i not in by_id]
        if missing:  # delivered earlier but no longer in the top-N pool window
            for a in live(self.repo.get_many(["A#" + i for i in missing]), now_ts):
                by_id[a["id"]] = a
        return [by_id[i] for i in ids if i in by_id]

    def _dtos(self, articles, mode, now_ts, now=None):
        ids = [a["id"] for a in articles]
        default = cached_rewrites(self.repo, ids, DEFAULT_MODE, now_ts)
        chosen = cached_rewrites(self.repo, ids, mode, now_ts) if mode != DEFAULT_MODE else default

        missing = [a for a in articles if a["id"] not in chosen]
        if missing and self._gemini_factory:
            client = self._gemini_factory()
            target_now = now or utcnow()
            if client and take_global_budget(self.repo, self.s, target_now):
                try:
                    res = client.rewrite_batch(missing, mode)
                    for a in missing:
                        if a["id"] in res:
                            self.repo.put_rewrite(a["id"], mode, res[a["id"]], now_ts + self.s.retention_days * 86400)
                            chosen[a["id"]] = res[a["id"]]
                except Exception as exc:
                    log("warning", "batch_rewrite_failed", error=str(exc))

        out = []
        for a in articles:
            head, used = (chosen.get(a["id"]), mode) if a["id"] in chosen else (default.get(a["id"]), DEFAULT_MODE)
            out.append(to_dto(a, head, used if head else None))
        return out

    def _ensure_usage(self, uid, day, pool, prefs, now):
        usage = self.repo.get_usage(uid, day)
        if usage is None or usage["fetchMoreCount"] == 0:
            ids = [a["id"] for a in select_stories(pool, prefs["mutedCategories"], self.s.briefing_size,
                                                   min_score=self.s.min_score)]
            if (usage is None and ids) or (usage and usage["delivered"] != ids):
                self.repo.set_initial_delivery(uid, day, ids, self._usage_expiry(now))
                usage = self.repo.get_usage(uid, day)
        return usage or {"fetchMoreCount": 0, "delivered": [], "requests": {}}

    # ---- use-cases -------------------------------------------------------
    def get_briefing(self, uid, now, mode=None):
        day, now_ts = briefing_day(now, self.s.timezone), int(now.timestamp())
        pool, prefs = self._pool(day, now_ts), self._prefs(uid)
        if mode and mode in MODES and mode != prefs.get("humourMode"):
            prefs["humourMode"] = mode
            self.repo.put_prefs(uid, prefs)
        usage = self._ensure_usage(uid, day, pool, prefs, now)
        muted = set(prefs["mutedCategories"])
        shown = [a for a in self._resolve(usage["delivered"], pool, now_ts) if a["category"] not in muted]
        if len(shown) < self.s.briefing_size:
            already = {a["id"] for a in shown}
            fillers = select_stories(pool, muted, self.s.briefing_size - len(shown),
                                     exclude_ids=already, min_score=self.s.min_score)
            shown.extend(fillers)
            # Update delivered list in usage so fetch-more doesn't duplicate them
            new_ids = [a["id"] for a in shown]
            if set(new_ids) != set(usage["delivered"]):
                self.repo.set_initial_delivery(uid, day, new_ids, self._usage_expiry(now))

        left = len(select_stories(pool, muted, 10 ** 6, [a["id"] for a in shown], self.s.min_score))
        remaining = max(0, self.s.max_fetch_more - usage["fetchMoreCount"])
        meta = (self.repo.get_many(["M#last_ingest"]) or [{}])[0]
        notice = None
        if usage["fetchMoreCount"] == 0 and len(shown) < self.s.briefing_size:
            notice = (f"Today's briefing has {len(shown)} stories. We only include verified stories "
                      "that meet our quality bar, so we never pad it to reach ten.")
        return {
            "date": day, "lastUpdated": meta.get("at"), "target": self.s.briefing_size,
            "articles": self._dtos(shown, prefs["humourMode"], now_ts, now), "total": len(shown),
            "activeCategories": [c for c in CATEGORIES if c not in muted],
            "categoryCounts": category_counts(pool, self.s.min_score), "notice": notice,
            "preferences": prefs,
            "fetchMore": {"used": usage["fetchMoreCount"], "max": self.s.max_fetch_more, "remaining": remaining,
                          "canFetchMore": remaining > 0 and left > 0, "exhausted": remaining == 0},
        }

    def fetch_more(self, uid, idem_key, now):
        day, now_ts = briefing_day(now, self.s.timezone), int(now.timestamp())
        pool, prefs = self._pool(day, now_ts), self._prefs(uid)
        for _ in range(3):  # lost races re-read and retry; the atomic write is the real gate
            usage = self._ensure_usage(uid, day, pool, prefs, now)
            if idem_key in usage["requests"]:
                batch = self._resolve(usage["requests"][idem_key], pool, now_ts)
                return self._fm_response(batch, usage, prefs, now_ts, replayed=True, now=now)
            if usage["fetchMoreCount"] >= self.s.max_fetch_more:
                raise ApiError(429, "FETCH_MORE_LIMIT_REACHED", "You've caught up with today's briefing.")
            picks = select_stories(pool, prefs["mutedCategories"], self.s.fetch_more_size,
                                   usage["delivered"], self.s.min_score)
            if not picks:  # nothing to deliver: do not burn quota
                return self._fm_response([], usage, prefs, now_ts, replayed=False, now=now)
            ids = [a["id"] for a in picks]
            if self.repo.commit_fetch_more(uid, day, usage["fetchMoreCount"], self.s.max_fetch_more, idem_key, ids):
                usage = self.repo.get_usage(uid, day)
                return self._fm_response(picks, usage, prefs, now_ts, replayed=False, now=now)
        raise ApiError(409, "CONFLICT", "Too many simultaneous requests. Please try again.")

    def _fm_response(self, batch, usage, prefs, now_ts, replayed, now=None):
        remaining = max(0, self.s.max_fetch_more - usage["fetchMoreCount"])
        return {"articles": self._dtos(batch, prefs["humourMode"], now_ts, now), "replayed": replayed,
                "fetchMore": {"used": usage["fetchMoreCount"], "max": self.s.max_fetch_more,
                              "remaining": remaining, "exhausted": remaining == 0}}

    def list_news(self, uid, category, offset, limit, now):
        day, now_ts = briefing_day(now, self.s.timezone), int(now.timestamp())
        usage = self.repo.get_usage(uid, day) or {"delivered": []}
        pool, prefs = self._pool(day, now_ts), self._prefs(uid)
        items = [a for a in self._resolve(usage["delivered"], pool, now_ts)
                 if a["category"] not in prefs["mutedCategories"] and (not category or a["category"] == category)]
        page = items[offset: offset + limit]
        return {"articles": self._dtos(page, prefs["humourMode"], now_ts), "total": len(items),
                "nextOffset": offset + limit if offset + limit < len(items) else None}

    def get_article(self, uid, article_id, now):
        now_ts = int(now.timestamp())
        rows = live(self.repo.get_many(["A#" + article_id]), now_ts)
        if not rows:
            raise ApiError(404, "NOT_FOUND", "Article not found or expired")
        return self._dtos(rows, self._prefs(uid)["humourMode"], now_ts)[0]

    def rewrite(self, uid, article_id, mode, now):
        day, now_ts = briefing_day(now, self.s.timezone), int(now.timestamp())
        usage = self.repo.get_usage(uid, day) or {"delivered": []}
        if article_id not in usage["delivered"]:
            raise ApiError(404, "NOT_FOUND", "Article not found in your briefing")
        rows = live(self.repo.get_many(["A#" + article_id]), now_ts)
        if not rows:
            raise ApiError(404, "NOT_FOUND", "Article not found or expired")
        hit = cached_rewrites(self.repo, [article_id], mode, now_ts)
        if article_id in hit:
            return {"articleId": article_id, "mode": mode, "headline": hit[article_id], "cached": True}
        exp = now_ts + 3 * 86400
        if not self.repo.take_quota(uid, f"RW#{day}", self.s.rewrite_user_daily_limit, 1, exp):
            raise ApiError(429, "REWRITE_QUOTA_REACHED", "Daily headline rewrite limit reached.")
        client = self._gemini_factory() if self._gemini_factory else None
        if client is None or not take_global_budget(self.repo, self.s, now):
            raise ApiError(503, "AI_UNAVAILABLE", "Headline rewriting is unavailable right now.")
        try:
            result = client.rewrite_batch([rows[0]], mode)
        except GeminiError as exc:
            log("error", "gemini_failed", error=str(exc))
            raise ApiError(503, "AI_UNAVAILABLE", "Headline rewriting is unavailable right now.")
        if article_id not in result:
            self.repo.put_rewrite(article_id, mode, rows[0]["title"], now_ts + self.s.retention_days * 86400)
            return {"articleId": article_id, "mode": mode, "headline": rows[0]["title"], "cached": False}
        self.repo.put_rewrite(article_id, mode, result[article_id], now_ts + self.s.retention_days * 86400)
        return {"articleId": article_id, "mode": mode, "headline": result[article_id], "cached": False}

    def get_summary(self, uid, article_id, now):
        day, now_ts = briefing_day(now, self.s.timezone), int(now.timestamp())
        rows = live(self.repo.get_many(["A#" + article_id]), now_ts)
        if not rows:
            raise ApiError(404, "NOT_FOUND", "Article not found or expired")
        art = rows[0]

        cache_row = (self.repo.get_many(["SM#" + article_id]) or [{}])[0]
        if cache_row.get("overview") and int(cache_row.get("expiresAt", 0)) > now_ts:
            return {"articleId": article_id, "overview": cache_row["overview"],
                    "keyPoints": cache_row.get("keyPoints", []), "cached": True}

        client = self._gemini_factory() if self._gemini_factory else None
        if client and take_global_budget(self.repo, self.s, now):
            try:
                res = client.summarize_article(art["title"], art.get("summary"), art.get("publisher", "News"))
                if res.get("overview"):
                    data = {"pk": "SM#" + article_id, "articleId": article_id,
                            "overview": res["overview"], "keyPoints": res["keyPoints"],
                            "expiresAt": now_ts + self.s.retention_days * 86400}
                    self.repo.put_meta("SM#" + article_id, data)
                    return {"articleId": article_id, "overview": res["overview"],
                            "keyPoints": res["keyPoints"], "cached": False}
            except Exception as exc:
                log("warning", "summary_gen_failed", articleId=article_id, error=str(exc))

        fallback_overview = art.get("summary") or art["title"]
        return {"articleId": article_id, "overview": fallback_overview,
                "keyPoints": [art["title"], f"Reported by {art.get('publisher')}"], "cached": False, "fallback": True}


def to_dto(a, ai_headline, ai_mode):
    img = a.get("image")
    return {
        "id": a["id"], "category": a["category"], "originalTitle": a["title"], "aiHeadline": ai_headline,
        "aiMode": ai_mode, "publisher": a["publisher"], "publishedAt": a["publishedAt"],
        "summary": a.get("summary"), "url": a["url"], "coverage": a.get("coverage", 1),
        "alsoReportedBy": a.get("alsoReportedBy", []),
        "image": ({"url": img["url"], "source": img["source"], "attribution": img.get("attribution"),
                   "alt": f"Image from {a['publisher']} for: {a['title']}"[:200], "status": img.get("status")}
                  if img else None),
    }
