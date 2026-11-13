"""HTTP API (API Gateway HTTP API, payload v2). One Lambda, small router, no framework."""
import base64
import hashlib
import hmac
import json
import re
import secrets as pysecrets

from shared.ai.personalities import DEFAULT_MODE
from shared.briefing.service import ApiError, BriefingService, DEFAULT_PREFS
from shared.secrets import resolve
from shared.utils import briefing_day, log, utcnow
from shared.validation import (ValidationError, validate_article_id, validate_idempotency_key,
                               validate_mode, validate_preferences)

_ROUTES = [
    ("GET", r"/api/health", "health", False),
    ("POST", r"/api/session", "session", False),
    ("GET", r"/api/briefing/today", "briefing", True),
    ("GET", r"/api/news", "news", True),
    ("POST", r"/api/news/fetch-more", "fetch_more", True),
    ("GET", r"/api/news/(?P<aid>[^/]+)", "article", True),
    ("GET", r"/api/news/(?P<aid>[^/]+)/summary", "summary", True),
    ("POST", r"/api/news/(?P<aid>[^/]+)/rewrite", "rewrite", True),
    ("GET", r"/api/preferences", "get_prefs", True),
    ("POST", r"/api/preferences", "put_prefs", True),
    ("PUT", r"/api/preferences", "put_prefs", True),
    ("DELETE", r"/api/preferences", "delete_prefs", True),
]


def _resp(status, body, headers=None):
    return {"statusCode": status, "body": json.dumps(body),
            "headers": {"Content-Type": "application/json", "Cache-Control": "no-store", **(headers or {})}}


def _error(status, code, message, request_id=None):
    return _resp(status, {"error": {"code": code, "message": message, "requestId": request_id}})


class App:
    def __init__(self, repo, settings, gemini_factory=None, now_fn=utcnow, pool_ttl=60):
        self.repo, self.s, self.now_fn = repo, settings, now_fn
        self.svc = BriefingService(repo, settings, gemini_factory, pool_ttl)

    # ---- anonymous identity: HMAC-signed bearer token, not strong authentication --------------
    def _secret(self):
        sec = resolve(self.s.session_secret, self.s.session_secret_param)
        if not sec:
            raise ApiError(500, "SERVER_MISCONFIGURED", "Server is not configured")
        return sec.encode()

    def _sign(self, uid):
        mac = hmac.new(self._secret(), uid.encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(mac).decode()[:22]

    def _auth(self, headers):
        token = (headers.get("authorization") or "").removeprefix("Bearer ").strip()
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != "v1" or not hmac.compare_digest(self._sign(parts[1]), parts[2]):
            raise ApiError(401, "UNAUTHORIZED", "Missing or invalid session token")
        return parts[1]

    # ---- dispatch --------------------------------------------------------------------------
    def handle(self, event):
        rid = (event.get("requestContext") or {}).get("requestId")
        method = event["requestContext"]["http"]["method"]
        path = event["rawPath"].rstrip("/") or "/"
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        try:
            for m, pattern, name, needs_auth in _ROUTES:
                match = re.fullmatch(pattern, path)
                if m == method and match:
                    uid = self._auth(headers) if needs_auth else None
                    return getattr(self, "_" + name)(event, headers, uid, match.groupdict())
            return _error(404, "NOT_FOUND", "Route not found", rid)
        except ValidationError as exc:
            return _error(404 if exc.code == "NOT_FOUND" else 400, exc.code, str(exc), rid)
        except ApiError as exc:
            return _error(exc.status, exc.code, str(exc), rid)
        except Exception as exc:  # never leak stack traces; they are in CloudWatch
            log("error", "unhandled", requestId=rid, error=repr(exc), path=path)
            return _error(500, "INTERNAL_ERROR", "Something went wrong. Please try again.", rid)

    @staticmethod
    def _json_body(event):
        raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode()
        if len(raw) > 4096:
            raise ValidationError("Body too large")
        try:
            return json.loads(raw)
        except ValueError:
            raise ValidationError("Body must be valid JSON")

    # ---- handlers --------------------------------------------------------------------------
    def _health(self, event, headers, uid, params):
        from shared.config import load_feeds
        feeds = load_feeds()
        rows = {r["feedId"]: r for r in self.repo.get_many(["S#" + f["id"] for f in feeds])}
        meta = (self.repo.get_many(["M#last_ingest"]) or [{}])[0]
        sources = [{"id": f["id"], "status": rows.get(f["id"], {}).get("status", "unknown"),
                    "lastSuccess": rows.get(f["id"], {}).get("lastSuccess"),
                    "consecutiveFailures": rows.get(f["id"], {}).get("consecutiveFailures", 0)} for f in feeds]
        return _resp(200, {"status": "ok", "lastIngest": meta.get("at"), "sources": sources})

    def _session(self, event, headers, uid, params):
        now = self.now_fn()
        ip = ((event.get("requestContext") or {}).get("http") or {}).get("sourceIp", "unknown")
        ip_hash = hmac.new(self._secret(), ip.encode(), hashlib.sha256).hexdigest()[:16]  # raw IP never stored
        day = briefing_day(now, self.s.timezone)
        if not self.repo.take_quota("Q#session", f"{ip_hash}#{day}", self.s.sessions_per_ip_daily, 1,
                                    int(now.timestamp()) + 3 * 86400):
            raise ApiError(429, "TOO_MANY_SESSIONS", "Too many new sessions from this network today.")
        new_uid = pysecrets.token_urlsafe(16)
        return _resp(201, {"token": f"v1.{new_uid}.{self._sign(new_uid)}"})

    def _briefing(self, event, headers, uid, params):
        q = event.get("queryStringParameters") or {}
        mode = q.get("mode")
        return _resp(200, self.svc.get_briefing(uid, self.now_fn(), mode=mode))

    def _news(self, event, headers, uid, params):
        q = event.get("queryStringParameters") or {}
        category = q.get("category")
        from shared.config.categories import CATEGORY_IDS
        if category and category not in CATEGORY_IDS:
            raise ValidationError("Unknown category")
        try:
            offset, limit = max(0, int(q.get("offset", 0))), min(30, max(1, int(q.get("limit", 10))))
        except ValueError:
            raise ValidationError("offset and limit must be integers")
        return _resp(200, self.svc.list_news(uid, category, offset, limit, self.now_fn()))

    def _fetch_more(self, event, headers, uid, params):
        key = validate_idempotency_key(headers.get("idempotency-key"))
        return _resp(200, self.svc.fetch_more(uid, key, self.now_fn()))

    def _article(self, event, headers, uid, params):
        return _resp(200, self.svc.get_article(uid, validate_article_id(params["aid"]), self.now_fn()))

    def _summary(self, event, headers, uid, params):
        aid = validate_article_id(params["aid"])
        return _resp(200, self.svc.get_summary(uid, aid, self.now_fn()))

    def _rewrite(self, event, headers, uid, params):
        aid = validate_article_id(params["aid"])
        body = self._json_body(event)
        mode = validate_mode(body.get("mode") or self.svc._prefs(uid)["humourMode"])
        return _resp(200, self.svc.rewrite(uid, aid, mode, self.now_fn()))

    def _get_prefs(self, event, headers, uid, params):
        return _resp(200, {**DEFAULT_PREFS, **(self.repo.get_prefs(uid) or {})})

    def _put_prefs(self, event, headers, uid, params):
        prefs = validate_preferences(self._json_body(event))
        self.repo.put_prefs(uid, prefs)
        self.svc._pool_cache.clear()
        return _resp(200, prefs)

    def _delete_prefs(self, event, headers, uid, params):
        self.repo.delete_prefs(uid)
        return _resp(200, DEFAULT_PREFS)
