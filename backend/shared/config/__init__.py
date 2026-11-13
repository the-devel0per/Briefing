import json
import os

from .settings import Settings


def load_feeds():
    with open(os.path.join(os.path.dirname(__file__), "sources.json"), encoding="utf-8") as fh:
        return json.load(fh)["feeds"]


__all__ = ["Settings", "load_feeds"]
