"""Pure briefing selection: category allocation, muting, reallocation, de-duplication of deliveries."""
from ..config.categories import CATEGORIES
from ..ingestion.dedupe import title_tokens


def live(articles, now_ts):
    """Application-level TTL: DynamoDB deletes lazily (up to ~48h), so never trust the table alone."""
    return [a for a in articles if int(a.get("expiresAt", 0)) > now_ts]


def select_stories(pool, muted, count, exclude_ids=(), min_score=0.0):
    """Pick up to `count` stories.

    1. Prioritizes hot topics that have authentic images (or extracted video/YT thumbnails).
    2. Strict deduplication: never picks two stories sharing the same image or near-duplicate topic.
    3. Each active category first gets its default slots (best stories first).
    4. Slots that cannot be filled (muted / thin category) are reallocated to remaining active categories.
    """
    excluded = set(exclude_ids)
    candidates = sorted(
        (a for a in pool if a["category"] not in muted and a["id"] not in excluded and a["score"] >= min_score),
        key=lambda a: (bool(a.get("image")), a.get("coverage", 1) >= 2, a["score"]), reverse=True)

    chosen, chosen_ids = [], set()
    chosen_images = set()

    def is_related(art):
        img_url = (art.get("image") or {}).get("url")
        if img_url and img_url in chosen_images:
            return True
        tokens = title_tokens(art.get("title", ""))
        info_tokens = {t for t in tokens if t not in {"story", "things", "about"}}
        if not info_tokens:
            return False
        for prev in chosen:
            prev_tokens = {t for t in title_tokens(prev.get("title", "")) if t not in {"story", "things", "about"}}
            if not prev_tokens:
                continue
            inter = info_tokens & prev_tokens
            if not inter:
                continue
            jaccard = len(inter) / len(info_tokens | prev_tokens)
            overlap = len(inter) / min(len(info_tokens), len(prev_tokens))
            if jaccard >= 0.5 or overlap >= 0.65:
                return True
            distinctive = {t for t in inter if len(t) > 3}
            # If same publisher or 2 distinctive entities match (e.g. "applied materials")
            if len(distinctive) >= 2 and (overlap >= 0.4 or art.get("publisher") == prev.get("publisher")):
                return True
        return False

    def add_story(a):
        chosen.append(a)
        chosen_ids.add(a["id"])
        if a.get("image") and a["image"].get("url"):
            chosen_images.add(a["image"]["url"])

    for cat, meta in CATEGORIES.items():
        if cat in muted:
            continue
        slots = meta["slots"]
        taken = 0
        for a in [c for c in candidates if c["category"] == cat]:
            if taken >= slots or len(chosen) >= count:
                break
            if a["id"] not in chosen_ids and not is_related(a):
                add_story(a)
                taken += 1

    for a in candidates:
        if len(chosen) >= count:
            break
        if a["id"] not in chosen_ids and not is_related(a):
            add_story(a)

    return sorted(chosen, key=lambda a: (bool(a.get("image")), a.get("coverage", 1) >= 2, a["score"]), reverse=True)


def category_counts(pool, min_score=0.0):
    counts = {c: 0 for c in CATEGORIES}
    for a in pool:
        if a["score"] >= min_score:
            counts[a["category"]] += 1
    return counts
