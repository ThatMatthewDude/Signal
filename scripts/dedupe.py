"""Step 2: cross-source dedupe, within this fetch and across past runs.

Two distinct kinds of duplicate are handled here, and both are about the
same *story* appearing under more than one source - never about hiding an
item just because it was already shown before. Skipping a day should cost
nothing: an unopened item stays in the feed under the normal cap/rotation in
render.py, not disappear because it's "already seen."
  1. Same story covered by multiple sources in *this* fetch (e.g. NYT and
     Reuters both running a wire story) - matched by URL or high title
     similarity within a short time window, keeping the fullest version.
  2. Same story covered by a *different* source than the one that broke it,
     discovered in an earlier cycle (data/seen.json) - dedupe_within_batch
     above only catches same-cycle duplicates, so this catches the case
     where e.g. NYT ran it this cycle and Reuters picks it up next cycle.
     A repeat from the *same* source is never dropped here.

Writes the surviving items to data/candidates.json and updates the pruned
data/seen.json store for next run.
"""
import sys
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from dateutil import parser as date_parser

from common import (
    CANDIDATES_PATH,
    FETCHED_RAW_PATH,
    SEEN_PATH,
    SEEN_STORE_MAX_AGE_DAYS,
    SEEN_STORE_MAX_SIZE,
    load_json,
    normalize_title,
    save_json,
)

TITLE_SIMILARITY_THRESHOLD = 0.82
CROSS_SOURCE_WINDOW_HOURS = 48


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_dt(value: str):
    try:
        return date_parser.isoparse(value)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def titles_similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= TITLE_SIMILARITY_THRESHOLD


def dedupe_within_batch(items: list) -> list:
    # Fuller items (full body text) are more valuable to keep as the canonical
    # copy when the same story is duplicated across sources.
    items = sorted(items, key=lambda it: it["snippet_only"])

    kept = []
    seen_urls = set()
    for item in items:
        if item["url"] in seen_urls:
            continue

        item_dt = parse_dt(item["published_at"])
        is_duplicate = False
        norm_title = normalize_title(item["title"])
        for kept_item in kept:
            kept_dt = parse_dt(kept_item["published_at"])
            if abs((item_dt - kept_dt).total_seconds()) > CROSS_SOURCE_WINDOW_HOURS * 3600:
                continue
            if titles_similar(norm_title, normalize_title(kept_item["title"])):
                is_duplicate = True
                break

        if is_duplicate:
            continue

        kept.append(item)
        seen_urls.add(item["url"])

    return kept


def filter_cross_source_duplicates(items: list, seen_store: list) -> list:
    """Drop items that re-cover a story a *different* source already broke in
    a past cycle. Never matches against the item's own source, so a source
    re-running its own item (it's still within fetch.py's recent-N window, or
    it's simply still the most recent thing it's published) is always kept -
    that repeat isn't hidden, it just competes normally for a cap/rotation
    slot in render.py like everything else.
    """
    other_source_entries = [
        (entry["source"], normalize_title(entry["title"]), parse_dt(entry["published_at"]))
        for entry in seen_store
        if entry.get("source")
    ]

    fresh = []
    for item in items:
        item_title = normalize_title(item["title"])
        item_dt = parse_dt(item["published_at"])
        is_duplicate = False
        for seen_source, seen_title, seen_dt in other_source_entries:
            if seen_source == item["source"]:
                continue
            if abs((item_dt - seen_dt).total_seconds()) > CROSS_SOURCE_WINDOW_HOURS * 3600:
                continue
            if titles_similar(item_title, seen_title):
                is_duplicate = True
                break

        if is_duplicate:
            continue
        fresh.append(item)

    return fresh


def update_seen_store(seen_store: list, candidates: list) -> list:
    """Merge this cycle's candidates into the store, keyed by id so a source
    re-fetching the same item every cycle doesn't pile up duplicate entries
    (it would otherwise crowd out the cross-source-matching history above).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    by_id = {entry["id"]: entry for entry in seen_store}
    for item in candidates:
        first_shown_at = by_id[item["id"]]["first_shown_at"] if item["id"] in by_id else now_iso
        by_id[item["id"]] = {
            "id": item["id"],
            "url": item["url"],
            "title": item["title"],
            "source": item["source"],
            "published_at": item["published_at"],
            "first_shown_at": first_shown_at,
        }
    return prune_seen_store(list(by_id.values()))


def prune_seen_store(seen_store: list) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=SEEN_STORE_MAX_AGE_DAYS)
    pruned = [entry for entry in seen_store if parse_dt(entry["published_at"]) >= cutoff]
    pruned.sort(key=lambda entry: entry["published_at"], reverse=True)
    return pruned[:SEEN_STORE_MAX_SIZE]


def main():
    raw = load_json(FETCHED_RAW_PATH, {"items": []})
    fetched_items = raw["items"]
    log(f"Fetched items this cycle: {len(fetched_items)}")

    deduped = dedupe_within_batch(fetched_items)
    log(f"After cross-source dedupe: {len(deduped)}")

    seen_store = load_json(SEEN_PATH, [])
    candidates = filter_cross_source_duplicates(deduped, seen_store)
    log(f"After removing cross-source duplicates of past items: {len(candidates)}")

    save_json(CANDIDATES_PATH, candidates)

    updated_seen_store = update_seen_store(seen_store, candidates)
    save_json(SEEN_PATH, updated_seen_store)
    log(f"Seen store size after merge/prune: {len(updated_seen_store)}")


if __name__ == "__main__":
    main()
