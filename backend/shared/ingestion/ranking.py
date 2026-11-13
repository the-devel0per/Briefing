"""Story ranking. Each signal is 0..1 and weights sum to 1, so the score is explainable."""
import math
import re

from ..config.categories import IMPACT_KEYWORDS
from ..utils import parse_iso

WEIGHTS = {"recency": 0.30, "credibility": 0.20, "coverage": 0.20, "impact": 0.20, "relevance": 0.10}
HALF_LIFE_HOURS = 12.0


def score_article(article, now):
    age_h = max(0.0, (now - parse_iso(article["publishedAt"])).total_seconds() / 3600)
    words = set(re.findall(r"[a-z0-9]+", article["title"].lower()))
    # `coverage` counts DISTINCT publishers, so a syndicated copy never inflates it (uniqueness).
    signals = {
        "recency": 0.5 ** (age_h / HALF_LIFE_HOURS),
        "credibility": article.get("credibility", 0.5),
        "coverage": min(1.0, math.log2(max(1, article.get("coverage", 1))) / math.log2(6)),
        "impact": min(1.0, sum(1 for k in IMPACT_KEYWORDS if k in words) / 2),
        "relevance": article.get("relevance", 0.3),
    }
    return round(sum(WEIGHTS[k] * v for k, v in signals.items()), 4)
