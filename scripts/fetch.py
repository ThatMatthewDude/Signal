"""Step 1: pull raw items from every source in config/sources.yml.

Writes data/fetched_raw.json - this cycle's fetch only, not deduped against
history yet (that's dedupe.py's job). One bad/slow source must never take
down the whole run, so every source fetch is individually wrapped.
"""
import sys
import time
from datetime import datetime, timezone

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

from common import CONFIG_PATH, FETCHED_RAW_PATH, MAX_ITEMS_PER_SOURCE_FETCH, item_id, save_json

REQUEST_TIMEOUT = 20
USER_AGENT = "SignalFeedBot/1.0 (personal non-commercial RSS reader)"
MAX_RETRIES = 3


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def get_with_retry(url: str) -> requests.Response:
    """GET with backoff on 429s. Reddit in particular rate-limits bursts of
    requests from one IP, which this pipeline produces by nature (~30 sources
    fetched back to back)."""
    delay = 2
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else delay
                time.sleep(wait)
                delay *= 2
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError:
            raise
        except Exception as e:
            last_exc = e
            time.sleep(delay)
            delay *= 2
    if last_exc:
        raise last_exc
    raise requests.exceptions.HTTPError(f"429 Too Many Requests (after {MAX_RETRIES} retries): {url}")


def struct_time_to_iso(struct_time) -> str:
    if not struct_time:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc).isoformat()


def first_srcset_url(srcset: str) -> str:
    return srcset.split(",")[0].strip().split(" ")[0]


def extract_images(html: str) -> list:
    """Pull <img> URLs out of an item's body HTML. Checks src first, then
    falls back to data-src/srcset/data-srcset - a lot of sites lazy-load
    images via those instead, which a src-only scrape would silently miss
    even though the markup and text otherwise came through fine."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            srcset = img.get("srcset") or img.get("data-srcset")
            if srcset:
                src = first_srcset_url(srcset)
        if src:
            images.append(src)
    return images


def entry_body_html(entry) -> tuple:
    """Return (body_html, is_full_body)."""
    content_list = entry.get("content")
    if content_list:
        full = content_list[0].get("value", "")
        if full and len(full) > len(entry.get("summary", "")):
            return full, True
    summary = entry.get("summary", "")
    return summary, False


def is_text_post(source_name: str) -> bool:
    return source_name.startswith("r/")


def fetch_generic_feed(source: dict) -> list:
    feed_url = source.get("feed_url")
    if not feed_url:
        log(f"  skip (no feed_url): {source['name']}")
        return []

    # Fetch bytes via requests (uses certifi's CA bundle) rather than handing the
    # URL straight to feedparser, whose own urllib-based fetch fails cert
    # verification against some hosts on this machine despite the cert being fine.
    try:
        resp = get_with_retry(feed_url)
    except Exception as e:
        log(f"  WARNING: failed to download feed for {source['name']}: {e}")
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        log(f"  WARNING: failed to parse feed for {source['name']}: {parsed.get('bozo_exception')}")
        return []

    items = []
    forced_snippet_only = bool(source.get("snippet_only"))
    text_post = is_text_post(source["name"])

    for entry in parsed.entries[:MAX_ITEMS_PER_SOURCE_FETCH]:
        url = entry.get("link", "")
        title = entry.get("title", "(untitled)")
        if not url:
            continue

        body_html, is_full = entry_body_html(entry)
        snippet_only = forced_snippet_only or not is_full

        published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = struct_time_to_iso(published_struct)

        # Extract regardless of text_post - Reddit's RSS embeds a real preview
        # image in the body HTML for image-post subreddits even though those
        # items render as a text_post card; panelize.py decides whether to
        # surface it.
        images = extract_images(body_html)

        items.append({
            "id": item_id(url),
            "title": title,
            "url": url,
            "source": source["name"],
            "tag": source["tag"],
            "cadence": source["cadence"],
            "body_html": "" if snippet_only else body_html,
            "snippet": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)[:600],
            "images": images,
            "published_at": published_at,
            "snippet_only": snippet_only,
            "text_post": text_post,
        })
    return items


def fetch_hacker_news(source: dict) -> list:
    api_base = source["api_base"]
    keywords = [k.lower() for k in source.get("keywords", [])]
    try:
        resp = requests.get(api_base + "topstories.json", timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        story_ids = resp.json()[:200]
    except Exception as e:
        log(f"  WARNING: failed to list Hacker News top stories: {e}")
        return []

    items = []
    for story_id in story_ids:
        if len(items) >= MAX_ITEMS_PER_SOURCE_FETCH:
            break
        try:
            item_resp = requests.get(f"{api_base}item/{story_id}.json", timeout=REQUEST_TIMEOUT)
            item_resp.raise_for_status()
            story = item_resp.json()
        except Exception as e:
            log(f"  WARNING: failed to fetch HN item {story_id}: {e}")
            continue

        if not story or story.get("type") != "story":
            continue
        title = story.get("title", "")
        if keywords and not any(kw in title.lower() for kw in keywords):
            continue

        url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        published_at = datetime.fromtimestamp(story.get("time", time.time()), tz=timezone.utc).isoformat()

        items.append({
            "id": item_id(url),
            "title": title,
            "url": url,
            "source": source["name"],
            "tag": source["tag"],
            "cadence": source["cadence"],
            "body_html": "",
            "snippet": story.get("text", "")[:600] if story.get("text") else f"{story.get('score', 0)} points, {story.get('descendants', 0)} comments",
            "images": [],
            "published_at": published_at,
            "snippet_only": True,
            "text_post": True,
        })
    return items


def build_arxiv_feed_url(api_base: str, category: str) -> str:
    return f"{api_base}?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&max_results=15"


def fetch_arxiv(source: dict) -> list:
    items = []
    for category in source.get("categories", []):
        pseudo_source = {
            "name": source["name"],
            "tag": source["tag"],
            "cadence": source["cadence"],
            "feed_url": build_arxiv_feed_url(source["api_base"], category),
            "snippet_only": True,
        }
        items.extend(fetch_generic_feed(pseudo_source))
        time.sleep(1)  # be polite to arXiv's API rate limit
    return items


def fetch_source(source: dict) -> list:
    source_type = source.get("type")
    if source_type == "api":
        provider = source.get("provider")
        if provider == "hacker_news":
            return fetch_hacker_news(source)
        if provider == "arxiv":
            return fetch_arxiv(source)
        log(f"  WARNING: unknown api provider '{provider}' for {source['name']}")
        return []
    return fetch_generic_feed(source)


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_items = []
    for source in config["sources"]:
        log(f"Fetching {source['name']}...")
        try:
            items = fetch_source(source)
        except Exception as e:
            log(f"  ERROR fetching {source['name']}: {e}")
            items = []
        log(f"  -> {len(items)} item(s)")
        all_items.extend(items)
        delay = 2.5 if "reddit.com" in (source.get("feed_url") or "") else 0.5
        time.sleep(delay)  # stay polite and avoid tripping rate limits (esp. Reddit)

    save_json(FETCHED_RAW_PATH, {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": all_items,
    })
    log(f"Total items fetched: {len(all_items)}")


if __name__ == "__main__":
    main()
