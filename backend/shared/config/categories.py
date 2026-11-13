"""Category definitions, default slot allocation and keyword signals."""

CATEGORIES = {
    "technology": {"label": "Technology", "slots": 3},
    "government": {"label": "Government & Policy", "slots": 2},
    "crypto": {"label": "Crypto", "slots": 3},
    "stocks": {"label": "Stocks & Markets", "slots": 2},
}
CATEGORY_IDS = tuple(CATEGORIES)

KEYWORDS = {
    "technology": ["ai", "software", "chip", "semiconductor", "startup", "cloud", "cyber", "openai",
                   "google", "apple", "microsoft", "nvidia", "robot", "quantum", "app", "data", "model"],
    "government": ["government", "senate", "congress", "parliament", "policy", "law", "regulation",
                   "bill", "court", "minister", "president", "election", "tariff", "sanction", "treaty"],
    "crypto": ["bitcoin", "ethereum", "crypto", "blockchain", "stablecoin", "token", "binance",
               "coinbase", "etf", "defi", "solana", "wallet"],
    "stocks": ["stock", "stocks", "shares", "market", "earnings", "nasdaq", "dow", "fed",
               "inflation", "rate", "ipo", "dividend", "bond", "wall", "sensex", "nifty"],
}

# Words that signal a story with broad consequences; used for the "impact" ranking signal.
IMPACT_KEYWORDS = ["ban", "bans", "record", "surge", "plunge", "crash", "lawsuit", "breach", "hack",
                   "acquire", "acquisition", "merger", "billion", "approves", "passes", "signs",
                   "launches", "raises", "cuts", "hike", "default", "bankruptcy", "investigation",
                   "outage", "shutdown", "war", "ceasefire", "recall", "layoffs"]
