"""HTTP feed fetching: allow-listed URLs only (they come from sources.json, never from users),
timeouts, bounded size, conditional GET and exponential backoff."""
import urllib.error
import urllib.request

from ..utils import log, sleep_backoff
from ..validation import is_http_url

MAX_BYTES = 2_000_000
UA = "DailyBriefingBot/1.0 (+personal news briefing; respects robots and rate limits)"


class FetchError(Exception):
    pass


def fetch_feed(feed, state, timeout, retries, opener=urllib.request.urlopen, sleep=None):
    """Returns {"status": "ok"|"not_modified", "body", "etag", "lastModified"}."""
    if not is_http_url(feed["url"], https_only=True):
        raise FetchError("feed url must be https")
    headers = {"User-Agent": UA, "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.5"}
    if state.get("etag"):
        headers["If-None-Match"] = state["etag"]
    if state.get("lastModified"):
        headers["If-Modified-Since"] = state["lastModified"]
    last_err = None
    for attempt in range(retries):
        try:
            with opener(urllib.request.Request(feed["url"], headers=headers), timeout=timeout) as resp:
                body = resp.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise FetchError("feed too large")
                return {"status": "ok", "body": body, "etag": resp.headers.get("ETag"),
                        "lastModified": resp.headers.get("Last-Modified")}
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return {"status": "not_modified", "body": None, "etag": state.get("etag"),
                        "lastModified": state.get("lastModified")}
            if exc.code < 500 and exc.code != 429:
                raise FetchError(f"HTTP {exc.code}") from exc  # permanent: do not hammer the publisher
            last_err = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_err = exc
        log("warning", "feed_retry", feed=feed["id"], attempt=attempt + 1, error=str(last_err))
        if attempt < retries - 1:
            (sleep_backoff(attempt) if sleep is None else sleep_backoff(attempt, sleep=sleep))
    raise FetchError(f"gave up after {retries} attempts: {last_err}")
