"""Post-generation checks. A rewrite that fails any check is discarded and the original headline is shown."""
import re

_NAME = re.compile(r"\b[A-Z][A-Za-z0-9&.-]{2,}\b")
_COMMON = {"The", "And", "For", "But", "With", "From", "After", "Over", "New", "How", "Why", "What",
           "Will", "Says", "Amid", "Into", "Could", "May", "Its", "Are", "Was", "Has", "Have", "Here", "Is"}
MAX_LEN = 220


def _numbers(s):
    return set(re.findall(r"\d+(?:\.\d+)?", s.replace(",", "")))


def is_acceptable(original, rewritten):
    r = (rewritten or "").strip()
    if not r or "\n" in r or len(r) > MAX_LEN or r.casefold() == original.strip().casefold():
        return False
    if not _numbers(original) <= _numbers(r):
        return False  # a number or date was changed or dropped
    words = original.split()[1:]  # first word is capitalised by grammar, not because it is a name
    names = {w.strip(".,:;!?\"'()") for w in words if _NAME.fullmatch(w.strip(".,:;!?\"'()"))} - _COMMON
    if names:
        kept = sum(1 for n in names if n.lower() in r.lower())
        if kept / len(names) < 0.5:
            return False  # company/person names must survive the joke
    return True
