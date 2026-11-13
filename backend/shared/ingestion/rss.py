"""RSS 2.0 parsing and article normalisation. Pure functions: no network, no AWS."""
import html
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..config.categories import KEYWORDS
from ..config.publishers import credibility, normalize_publisher
from ..utils import clean_text, iso, parse_iso, stable_id
from ..validation import is_http_url

MEDIA = "{http://search.yahoo.com/mrss/}"
_TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|cmpid)", re.I)


class FeedParseError(Exception):
    pass


def parse_date(value):
    """Return an aware UTC datetime or None. Accepts RFC 822 and ISO 8601."""
    if not value:
        return None
    from datetime import datetime, timezone
    try:
        dt = parsedate_to_datetime(value.strip())
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def canonical_url(url):
    p = urlparse(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if not _TRACKING.match(k)])
    return urlunparse((p.scheme, p.netloc.lower(), p.path, "", query, ""))


def _image_from_item(item, publisher):
    """Pick the widest image from media:thumbnail/content or an image enclosure."""
    candidates = []
    for el in list(item.iter(MEDIA + "thumbnail")) + list(item.iter(MEDIA + "content")):
        medium, mtype = el.get("medium"), el.get("type", "")
        if el.tag == MEDIA + "content" and not (medium == "image" or mtype.startswith("image/")):
            continue
        candidates.append((int(el.get("width") or 0), el.get("url")))
    enc = item.find("enclosure")
    if enc is not None and enc.get("type", "").startswith("image/"):
        candidates.append((0, enc.get("url")))
    for _, raw_url in sorted((c for c in candidates if c[1]), key=lambda c: -c[0]):
        url = html.unescape(raw_url.strip())
        if is_http_url(url, https_only=True):
            return {"url": url, "source": "rss", "attribution": f"Image: {publisher}", "status": "unverified"}

    # Check direct item link for YouTube URL
    link = (item.findtext("link") or "").strip()
    yt_link = re.search(r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})', link)
    if yt_link:
        return {"url": f"https://img.youtube.com/vi/{yt_link.group(1)}/hqdefault.jpg",
                "source": "youtube_thumbnail", "attribution": f"Image: {publisher or 'YouTube'}", "status": "unverified"}

    # Check embedded <img>, video poster, or YouTube thumbnail in description or content:encoded
    content_encoded = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
    for text in (item.findtext("description"), content_encoded):
        if text:
            m = re.search(r'<img[^>]+src=["\'](https://[^\s"\']+\.(?:jpg|jpeg|png|webp)[^\s"\']*)["\']', text, re.I)
            if m:
                url = html.unescape(m.group(1).strip())
                if is_http_url(url, https_only=True):
                    return {"url": url, "source": "rss_html", "attribution": f"Image: {publisher}", "status": "unverified"}
            vposter = re.search(r'<video[^>]+poster=["\'](https://[^\s"\']+)["\']', text, re.I)
            if vposter:
                url = html.unescape(vposter.group(1).strip())
                if is_http_url(url, https_only=True):
                    return {"url": url, "source": "video_poster", "attribution": f"Image: {publisher}", "status": "unverified"}
            yt = re.search(r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})', text)
            if yt:
                return {"url": f"https://img.youtube.com/vi/{yt.group(1)}/hqdefault.jpg",
                        "source": "youtube_thumbnail", "attribution": f"Image: {publisher or 'YouTube'}", "status": "unverified"}
    return None


def _strip_publisher_suffix(title, publisher):
    suffix = f" - {publisher}"
    return title[: -len(suffix)] if publisher and title.endswith(suffix) else title


def classify_relevance(title, category):
    words = set(re.findall(r"[a-z0-9&]+", title.lower()))
    hits = sum(1 for k in KEYWORDS[category] if k in words)
    return max(0.3, min(1.0, hits / 2))


def parse_feed(xml_bytes, feed, now, max_age_hours):
    """Parse one feed into normalised article dicts. Raises FeedParseError for unusable XML.
    Individual invalid items are dropped silently (counted by the caller via len())."""
    head = xml_bytes[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        # Rejects entity-expansion (billion laughs) / XXE payloads outright.
        raise FeedParseError("DOCTYPE/ENTITY declarations are not allowed")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise FeedParseError(f"invalid XML: {exc}") from exc
    if root.tag != "rss":
        raise FeedParseError("only RSS 2.0 feeds are supported")

    articles, oldest = [], now - timedelta(hours=max_age_hours)
    for item in root.iter("item"):
        raw_title, link = clean_text(item.findtext("title")), (item.findtext("link") or "").strip()
        published = parse_date(item.findtext("pubDate"))
        if not raw_title or not is_http_url(link) or published is None:
            continue
        if published > now + timedelta(hours=1) or published < oldest:
            continue
        src = item.find("source")
        if feed["type"] == "google":
            publisher = normalize_publisher(src.text if src is not None and src.text else "")
            summary = None  # Google's description is a list of related links, not a summary.
        else:
            publisher = normalize_publisher(feed.get("publisher", ""))
            summary = clean_text(item.findtext("description"))[:240] or None
        title = _strip_publisher_suffix(raw_title, publisher)
        url = canonical_url(link)
        articles.append({
            "id": stable_id(url), "category": feed["category"], "title": title, "publisher": publisher,
            "url": url, "publishedAt": iso(published), "summary": summary,
            "image": _image_from_item(item, publisher), "coverage": 1, "alsoReportedBy": [],
            "credibility": credibility(publisher), "relevance": classify_relevance(title, feed["category"]),
            "sourceFeed": feed["id"],
        })
    return articles


def published_dt(article):
    return parse_iso(article["publishedAt"])
