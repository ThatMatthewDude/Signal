"""Step 3: turn each candidate item's body into carousel panels.

Content fidelity is the whole point here: wording and images are never
altered, summarized, or rewritten - only re-paginated at paragraph
boundaries. Panel shapes:
  {"type": "text", "content": "..."}
  {"type": "image", "src": "...", "alt": "..."}
  {"type": "snippet", "content": "...", "read_more_url": "...", "read_more_source": "..."}
  {"type": "text_post", "content": "..."}   # Reddit / Hacker News style items
"""
import sys

from bs4 import BeautifulSoup

from common import CANDIDATES_PATH, PANELIZED_PATH, load_json, save_json

CHUNK_TARGET_CHARS = 700


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def chunk_article_body(body_html: str) -> list:
    soup = BeautifulSoup(body_html, "html.parser")
    elements = soup.find_all(["p", "img"])

    panels = []
    buffer_parts = []
    buffer_len = 0

    def flush_buffer():
        nonlocal buffer_parts, buffer_len
        if buffer_parts:
            panels.append({"type": "text", "content": "\n\n".join(buffer_parts)})
            buffer_parts = []
            buffer_len = 0

    for el in elements:
        if el.name == "img":
            src = el.get("src")
            if not src:
                continue
            flush_buffer()
            panels.append({"type": "image", "src": src, "alt": el.get("alt", "")})
            continue

        text = el.get_text(" ", strip=True)
        if not text:
            continue
        buffer_parts.append(text)
        buffer_len += len(text)
        if buffer_len >= CHUNK_TARGET_CHARS:
            flush_buffer()

    flush_buffer()
    return panels


def panelize_item(item: dict) -> list:
    if item.get("text_post"):
        content = item.get("snippet") or item.get("title")
        # Reddit's RSS embeds a real preview image for image-post subreddits
        # even though the item is otherwise a text_post card (e.g. r/Minecraft
        # screenshots) - surface it as a leading image panel, same as article
        # images, ahead of the text_post panel. Genuine self-text posts (no
        # <img> in the body) are unaffected - images is just empty.
        panels = [{"type": "image", "src": src, "alt": item.get("title", "")}
                  for src in item.get("images", [])]
        panels.append({"type": "text_post", "content": content})
        return panels

    if item.get("snippet_only") or not item.get("body_html"):
        return [{
            "type": "snippet",
            "content": item.get("snippet", ""),
            "read_more_url": item["url"],
            "read_more_source": item["source"],
        }]

    panels = chunk_article_body(item["body_html"])
    if not panels:
        return [{
            "type": "snippet",
            "content": item.get("snippet", ""),
            "read_more_url": item["url"],
            "read_more_source": item["source"],
        }]
    return panels


def main():
    candidates = load_json(CANDIDATES_PATH, [])
    for item in candidates:
        item["panels"] = panelize_item(item)
    save_json(PANELIZED_PATH, candidates)
    log(f"Panelized {len(candidates)} item(s)")


if __name__ == "__main__":
    main()
