"""Near-duplicate story detection using token overlap on normalised headlines."""
import re

_STOP = set("the a an of to in on for and or as at by with from is are was be after over new says say "
            "will its it this that into amid how why what who us vs".split())


def title_tokens(title):
    return frozenset(t for t in re.findall(r"[a-z0-9]+", title.lower()) if len(t) > 2 and t not in _STOP)


def similarity(a, b):
    if not a or not b:
        return 0.0
    common = a & b
    if not common:
        return 0.0
    inter = len(common)
    jaccard = inter / len(a | b)
    overlap = inter / min(len(a), len(b))
    distinctive = {t for t in common if len(t) > 3}
    if len(distinctive) >= 2 and overlap >= 0.4:
        return max(jaccard, overlap, 0.65)
    # overlap coefficient catches "X" vs "X: what we know" but only with enough shared tokens
    return max(jaccard, overlap * 0.9 if inter >= 3 else 0.0)


def find_duplicate(tokens, candidates, threshold=0.6):
    """candidates: iterable of (key, tokens). Returns the best-matching key or None."""
    best, best_sim = None, threshold
    for key, other in candidates:
        s = similarity(tokens, other)
        if s >= best_sim:
            best, best_sim = key, s
    return best
