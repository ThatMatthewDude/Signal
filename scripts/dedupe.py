"""Step 2: cross-source dedupe + cross-run seen-tracking.

Two distinct kinds of duplicate are handled here:
  1. Same story covered by multiple sources in *this* fetch (e.g. NYT and
     Reuters both running a wire story) - matched by URL or high title
     similarity within a short time window, keeping the fullest version.
  2. An item that was already shown in a *previous* cycle's rendered feed
     (data/seen.json) - dropped so the feed only ever surfaces things the
     user hasn't seen yet, keeping the "something new" feel bounded rather
     than an ever-growing archive or a rehash of yesterday's items.

Writes the surviving, genuinely-new items to data/candidates.json and
updates the pruned data/seen.json store for next run.
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


def filter_already_seen(items: list, seen_store: list) -> list:
    seen_ids = {entry["id"] for entry in seen_store}
    seen_titles = [(normalize_title(entry["title"]), parse_dt(entry["published_at"])) for entry in seen_store]

    fresh = []
    for item in items:
        if item["id"] in seen_ids:
            continue

        item_title = normalize_title(item["title"])
        item_dt = parse_dt(item["published_at"])
        already_shown = False
        for seen_title, seen_dt in seen_titles:
            if abs((item_dt - seen_dt).total_seconds()) > CROSS_SOURCE_WINDOW_HOURS * 3600:
                continue
            if titles_similar(item_title, seen_title):
                already_shown = True
                break

        if already_shown:
            continue
        fresh.append(item)

    return fresh


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
    candidates = filter_already_seen(deduped, seen_store)
    log(f"After removing already-seen items: {len(candidates)}")

    save_json(CANDIDATES_PATH, candidates)

    now_iso = datetime.now(timezone.utc).isoformat()
    new_seen_entries = [
        {
            "id": item["id"],
            "url": item["url"],
            "title": item["title"],
            "published_at": item["published_at"],
            "first_shown_at": now_iso,
        }
        for item in candidates
    ]
    updated_seen_store = prune_seen_store(seen_store + new_seen_entries)
    save_json(SEEN_PATH, updated_seen_store)
    log(f"Seen store size after prune: {len(updated_seen_store)}")


if __name__ == "__main__":
    main()
