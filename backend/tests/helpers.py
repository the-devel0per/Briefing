import json
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from shared.config import Settings
from shared.config.categories import CATEGORY_IDS
from shared.repositories.memory import MemoryRepository
from shared.utils import iso, stable_id

NOW = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc)
SECRET = "test-secret"


def settings(**over):
    import os
    os.environ.update(SESSION_SECRET=SECRET)
    s = Settings.from_env()
    return Settings(**{**s.__dict__, **over})


def rss(items, ns=True):
    body = "".join(
        f"<item><title>{t}</title><link>{l}</link><pubDate>{format_datetime(p)}</pubDate>{extra}</item>"
        for t, l, p, extra in items)
    return (f'<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">'
            f"<channel><title>x</title>{body}</channel></rss>").encode()


def seed_pool(repo, n=40, now=NOW, s=None):
    """n live articles, descending scores, categories round-robin."""
    s = s or settings()
    for i in range(n):
        repo.put_article({
            "id": stable_id(f"u{i}"), "category": CATEGORY_IDS[i % 4], "title": f"Story {i} about things",
            "publisher": "Reuters", "url": f"https://example.com/{i}", "publishedAt": iso(now - timedelta(hours=1)),
            "summary": None, "image": None, "coverage": 1, "alsoReportedBy": [], "score": round(0.9 - i * 0.01, 4),
            "day": "2026-11-13", "expiresAt": int(now.timestamp()) + 86400, "credibility": 0.9, "relevance": 0.5})
    return repo


def event(method, path, token=None, body=None, headers=None, query=None, ip="1.2.3.4"):
    h = {"authorization": f"Bearer {token}"} if token else {}
    h.update(headers or {})
    return {"rawPath": path, "headers": h, "queryStringParameters": query,
            "body": json.dumps(body) if body is not None else None,
            "requestContext": {"requestId": "req-1", "http": {"method": method, "sourceIp": ip}}}
