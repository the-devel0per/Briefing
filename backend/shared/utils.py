import hashlib
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_log = logging.getLogger("news")


def log(level, event, **fields):
    """Structured (JSON) logging so CloudWatch Logs Insights can query fields."""
    if not _log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(message)s"))
        _log.addHandler(h)
        _log.setLevel(logging.INFO)
    _log.log(getattr(logging, level.upper()), json.dumps({"event": event, **fields}, default=str))


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def briefing_day(now, tz_name):
    """The daily briefing cycle is defined in a configurable timezone."""
    return now.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d")


def previous_day(day):
    from datetime import date, timedelta
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def stable_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


_ws = re.compile(r"\s+")


def clean_text(s):
    import html
    s = re.sub(r"<[^>]+>", " ", html.unescape(s or ""))
    return _ws.sub(" ", html.unescape(s)).strip()


def sleep_backoff(attempt, base=0.5, sleep=time.sleep):
    import random
    sleep(base * (2 ** attempt) + random.random() * 0.25)
