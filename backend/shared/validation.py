"""Input validation. Everything that crosses the API boundary goes through here."""
import re
from urllib.parse import urlparse

from .config.categories import CATEGORY_IDS
from .ai.personalities import MODES


class ValidationError(Exception):
    def __init__(self, message, code="INVALID_REQUEST"):
        super().__init__(message)
        self.code = code


_KEY = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_ID = re.compile(r"^[a-f0-9]{16}$")


def validate_preferences(body):
    if not isinstance(body, dict):
        raise ValidationError("Body must be a JSON object")
    muted = body.get("mutedCategories", [])
    mode = body.get("humourMode", "witty")
    if not isinstance(muted, list) or any(c not in CATEGORY_IDS for c in muted):
        raise ValidationError("mutedCategories must be a list of valid category ids")
    if len(set(muted)) >= len(CATEGORY_IDS):
        raise ValidationError("At least one category must stay active")
    if mode not in MODES:
        raise ValidationError("humourMode is not supported")
    return {"mutedCategories": sorted(set(muted)), "humourMode": mode}


def validate_idempotency_key(key):
    if not isinstance(key, str) or not _KEY.match(key):
        raise ValidationError("Idempotency-Key header must be 8-64 chars [A-Za-z0-9_-]")
    return key


def validate_article_id(article_id):
    if not isinstance(article_id, str) or not _ID.match(article_id):
        raise ValidationError("Invalid article id", "NOT_FOUND")
    return article_id


def validate_mode(mode):
    if mode not in MODES:
        raise ValidationError("humourMode is not supported")
    return mode


def is_http_url(url, https_only=False):
    try:
        p = urlparse(url)
    except ValueError:
        return False
    schemes = ("https",) if https_only else ("http", "https")
    return p.scheme in schemes and bool(p.hostname) and len(url) <= 2048
