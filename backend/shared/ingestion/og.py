"""Optional Open Graph image discovery for DIRECT publisher links (disabled by default).
Safety: https only, public IPs only (also re-checked on every redirect), robots.txt honoured,
small byte cap. URLs only ever come from curated feeds, never from user input."""
import ipaddress
import re
import socket
import urllib.request
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from .fetcher import UA

_META = re.compile(r"<meta[^>]+>", re.I)


def _public_host(url):
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or (p.port not in (None, 443)):
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    return all(ipaddress.ip_address(i[4][0]).is_global for i in infos)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _public_host(newurl):
            raise urllib.error.URLError("redirect to non-public host blocked")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _get(url, max_bytes, timeout=5):
    if not _public_host(url):
        raise ValueError("blocked url")
    opener = urllib.request.build_opener(_SafeRedirect)
    with opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
        return r.read(max_bytes), r.headers.get("Content-Type", "")


def allowed_by_robots(url):
    p = urlparse(url)
    try:
        body, _ = _get(f"https://{p.hostname}/robots.txt", 100_000)
    except Exception:
        return False  # when in doubt, do not fetch
    rp = RobotFileParser()
    rp.parse(body.decode("utf-8", "ignore").splitlines())
    return rp.can_fetch(UA, url)


def extract_og_image(html):
    for tag in _META.findall(html):
        if re.search(r'(property|name)=["\']og:image["\']', tag, re.I):
            m = re.search(r'content=["\']([^"\']+)["\']', tag, re.I)
            if m and m.group(1).startswith("https://"):
                return m.group(1)
    return None


def fetch_og_image(url):
    if not allowed_by_robots(url):
        return None
    body, ctype = _get(url, 256_000)
    if "html" not in ctype.lower():
        return None
    return extract_og_image(body.decode("utf-8", "ignore"))
