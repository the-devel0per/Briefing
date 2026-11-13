"""Publisher normalisation and credibility priors (0..1). Tune freely; unknown publishers get DEFAULT."""
DEFAULT_CREDIBILITY = 0.5

CREDIBILITY = {
    "reuters": 0.95, "associated press": 0.95, "bbc news": 0.9, "bloomberg": 0.9,
    "financial times": 0.9, "the wall street journal": 0.9, "the new york times": 0.9,
    "the washington post": 0.85, "the guardian": 0.85, "cnbc": 0.8, "ars technica": 0.8, "wired": 0.8,
    "mit technology review": 0.85, "techcrunch": 0.75, "the verge": 0.75, "coindesk": 0.75,
    "marketwatch": 0.75, "the economist": 0.9, "politico": 0.8, "axios": 0.8, "cointelegraph": 0.65,
    "forbes": 0.65, "yahoo finance": 0.65, "the hill": 0.8, "fortune": 0.8, "decrypt": 0.75, "9to5mac": 0.75,
    "benzinga": 0.75,
}

ALIASES = {"bbc": "BBC News", "ap": "Associated Press", "wsj": "The Wall Street Journal",
           "nytimes": "The New York Times", "reuters.com": "Reuters", "guardian": "The Guardian"}


def normalize_publisher(name):
    name = " ".join((name or "").split()).strip(" -|")
    return ALIASES.get(name.lower(), name) or "Unknown"


def credibility(name):
    return CREDIBILITY.get(name.lower(), DEFAULT_CREDIBILITY)
