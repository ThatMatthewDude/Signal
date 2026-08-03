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
