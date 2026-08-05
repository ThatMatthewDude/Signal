"""Shared helpers used across the fetch -> dedupe -> panelize -> render pipeline."""
import hashlib
import json
import sys
from pathlib import Path

# Windows terminals default to a legacy codepage; source names/titles are
# frequently non-ASCII (em dashes, accents), which otherwise garbles stderr logs.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.yml"
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

FETCHED_RAW_PATH = DATA_DIR / "fetched_raw.json"
SEEN_PATH = DATA_DIR / "seen.json"
CANDIDATES_PATH = DATA_DIR / "candidates.json"
PANELIZED_PATH = DATA_DIR / "panelized.json"

MAX_ITEMS_PER_SOURCE_FETCH = 20   # per-source cap on a single fetch, keeps volume bounded
SEEN_STORE_MAX_AGE_DAYS = 30      # prune items older than this from the rolling store
SEEN_STORE_MAX_SIZE = 400         # hard cap on rolling store size regardless of age
FEED_DISPLAY_CAP = 45             # items actually rendered in the published feed

# The fixed set of tags sources.yml entries may use (also the badge text shown on
# each card). Low-frequency tags would otherwise be crowded out of a pure
# reverse-chronological cap by high-frequency ones (news/financial post many times
# a day; philosophy/engineering/fun blogs post far less) - MIN_SLOTS_PER_TAG is a
# static, transparent floor: each tag gets this many of its own most-recent items
# guaranteed a slot, and whatever's left up to FEED_DISPLAY_CAP fills by pure
# global recency across everything. Tune either constant to rebalance.
TAGS = ["news", "financial", "philosophy", "engineering", "fun"]
MIN_SLOTS_PER_TAG = 7

# A single high-volume source can otherwise dominate a tag's slots the same way a
# high-volume tag would dominate the whole feed without MIN_SLOTS_PER_TAG above -
# e.g. an aggregator source (many papers/authors under one feed entry) or just a
# very active subreddit. MAX_PER_SOURCE_PER_TAG is a hard cap, applied per (tag,
# source) pair during selection, on how many items any single source can
# contribute to a tag per refresh cycle - covers both the floor allocation and the
# open recency fill. General rule, not tied to any particular source.
MAX_PER_SOURCE_PER_TAG = 3


def item_id(url: str) -> str:
    return hashlib.sha1(url.strip().encode("utf-8")).hexdigest()[:16]


def load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_title(title: str) -> str:
    return " ".join(title.lower().split())
