"""Step 4: render the final static docs/index.html feed.

Single self-contained HTML file: embedded CSS, embedded item JSON, and a
small vanilla-JS layer that handles the swipeable carousel, relative
timestamps, and the localStorage-backed save/saved-view feature. No build
step, no server - GitHub Pages just serves this file as-is.
"""
import json
import sys
from datetime import datetime, timezone
from dateutil import parser as date_parser

from common import DOCS_DIR, FEED_DISPLAY_CAP, PANELIZED_PATH, load_json


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def parse_dt(value: str):
    try:
        return date_parser.isoparse(value)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def build_feed_items(all_items: list) -> list:
    sorted_items = sorted(all_items, key=lambda it: parse_dt(it["published_at"]), reverse=True)
    capped = sorted_items[:FEED_DISPLAY_CAP]

    feed_items = []
    for item in capped:
        feed_items.append({
            "id": item["id"],
            "title": item["title"],
            "url": item["url"],
            "source": item["source"],
            "tag": item["tag"],
            "published_at": item["published_at"],
            "panels": item["panels"],
            "text_post": bool(item.get("text_post")),
        })
    return feed_items


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Signal</title>
<style>
:root {{
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  padding: 0;
  background: #000;
  color: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}}
a {{ color: inherit; }}

.topbar {{
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: rgba(0,0,0,0.92);
  border-bottom: 1px solid #262626;
  backdrop-filter: blur(6px);
}}
.wordmark {{
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.02em;
}}
.icon-btn {{
  background: none;
  border: none;
  cursor: pointer;
  color: #f5f5f5;
  padding: 6px;
  display: flex;
  align-items: center;
}}
.icon-btn svg {{ width: 24px; height: 24px; }}

main {{
  max-width: 470px;
  margin: 0 auto;
  padding-bottom: 60px;
}}

.post {{
  border-bottom: 1px solid #1c1c1c;
  padding: 14px 0 22px;
  margin-bottom: 8px;
}}
.post-header {{
  display: flex;
  align-items: center;
  padding: 0 14px 10px;
  gap: 10px;
}}
.avatar {{
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #333;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: #ccc;
  flex-shrink: 0;
}}
.header-text {{
  display: flex;
  flex-direction: column;
  line-height: 1.25;
  min-width: 0;
}}
.source-name {{
  font-weight: 600;
  font-size: 13.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.header-meta {{
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}}
.tag-pill {{
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 999px;
  background: #1e1e1e;
  color: #aaa;
  border: 1px solid #2c2c2c;
  white-space: nowrap;
}}
.timestamp {{
  font-size: 12px;
  color: #8a8a8a;
  white-space: nowrap;
}}

.media {{
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  background: #0c0c0c;
  overflow: hidden;
}}
.carousel-track {{
  display: flex;
  height: 100%;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}}
.carousel-track::-webkit-scrollbar {{ display: none; }}
.panel {{
  min-width: 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 22px;
  overflow-y: auto;
}}
.panel img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
}}
.panel-text {{
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  color: #eee;
  align-self: flex-start;
  margin: auto 0;
}}
.panel-snippet {{
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-self: center;
}}
.panel-snippet p {{
  font-size: 15px;
  line-height: 1.6;
  color: #eee;
  margin: 0;
}}
.read-more {{
  font-size: 13.5px;
  font-weight: 600;
  color: #4ea1ff;
  text-decoration: none;
}}

.dots {{
  position: absolute;
  bottom: 10px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  gap: 5px;
}}
.dot {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.35);
}}
.dot.active {{ background: #fff; }}

.post-footer {{
  display: flex;
  align-items: center;
  padding: 10px 14px 0;
  gap: 12px;
}}
.save-btn {{
  background: none;
  border: none;
  cursor: pointer;
  color: #f5f5f5;
  padding: 4px;
  margin-left: auto;
}}
.save-btn svg {{ width: 22px; height: 22px; }}
.caption {{
  padding: 8px 14px 0;
  font-size: 13.5px;
  color: #ccc;
  line-height: 1.5;
}}
.caption .caption-source {{
  font-weight: 600;
  color: #f5f5f5;
  margin-right: 6px;
}}
.caption a {{
  color: #4ea1ff;
  text-decoration: none;
}}

#saved-view {{
  display: none;
}}
#saved-view.active {{ display: block; }}
#feed-view.hidden {{ display: none; }}
.empty-state {{
  text-align: center;
  color: #777;
  padding: 60px 20px;
  font-size: 14px;
}}
.saved-header {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 14px 14px;
}}
.saved-header h2 {{
  font-size: 16px;
  margin: 0;
}}
</style>
</head>
<body>

<div class="topbar">
  <div class="wordmark" id="wordmark-btn">Signal</div>
  <button class="icon-btn" id="saved-toggle-btn" aria-label="Saved posts">
    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 3c-1.1 0-2 .9-2 2v16l8-5.333L20 21V5c0-1.1-.9-2-2-2H6z"/></svg>
  </button>
</div>

<main>
  <div id="feed-view"></div>
  <div id="saved-view">
    <div class="saved-header">
      <button class="icon-btn" id="back-btn" aria-label="Back to feed">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
      </button>
      <h2>Saved</h2>
    </div>
    <div id="saved-list"></div>
  </div>
</main>

<script type="application/json" id="feed-data">{feed_json}</script>
<script>
{app_js}
</script>
</body>
</html>
"""


APP_JS = r"""
const FEED_ITEMS = JSON.parse(document.getElementById('feed-data').textContent);
const SAVE_KEY = 'signal-saved';

function getSaved() {
  try {
    return JSON.parse(localStorage.getItem(SAVE_KEY)) || [];
  } catch (e) {
    return [];
  }
}
function setSaved(list) {
  localStorage.setItem(SAVE_KEY, JSON.stringify(list));
}
function isSaved(id) {
  return getSaved().some(p => p.id === id);
}
function toggleSave(item) {
  const saved = getSaved();
  const idx = saved.findIndex(p => p.id === item.id);
  if (idx >= 0) {
    saved.splice(idx, 1);
  } else {
    saved.unshift(item);
  }
  setSaved(saved);
}

function relativeTime(iso) {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffSec = Math.max(0, Math.floor((now - then) / 1000));
  if (diffSec < 60) return 'now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return diffMin + 'm';
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return diffHr + 'h';
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return diffDay + 'd';
  const diffWeek = Math.floor(diffDay / 7);
  if (diffWeek < 5) return diffWeek + 'w';
  const diffMonth = Math.floor(diffDay / 30);
  return diffMonth + 'mo';
}

function initials(name) {
  const clean = name.replace(/^r\//, '');
  return clean.slice(0, 1).toUpperCase();
}

function renderPanel(panel) {
  if (panel.type === 'image') {
    const img = document.createElement('img');
    img.src = panel.src;
    img.alt = panel.alt || '';
    img.loading = 'lazy';
    return img;
  }
  if (panel.type === 'snippet') {
    const wrap = document.createElement('div');
    wrap.className = 'panel-snippet';
    const p = document.createElement('p');
    p.textContent = panel.content;
    wrap.appendChild(p);
    const a = document.createElement('a');
    a.className = 'read-more';
    a.href = panel.read_more_url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.textContent = 'Read the rest at ' + panel.read_more_source + ' →';
    wrap.appendChild(a);
    return wrap;
  }
  const div = document.createElement('div');
  div.className = 'panel-text';
  div.textContent = panel.content;
  return div;
}

function buildCard(item) {
  const post = document.createElement('article');
  post.className = 'post';

  const header = document.createElement('div');
  header.className = 'post-header';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = initials(item.source);
  header.appendChild(avatar);

  const headerText = document.createElement('div');
  headerText.className = 'header-text';
  const sourceName = document.createElement('div');
  sourceName.className = 'source-name';
  sourceName.textContent = item.source;
  headerText.appendChild(sourceName);
  header.appendChild(headerText);

  const meta = document.createElement('div');
  meta.className = 'header-meta';
  const tagPill = document.createElement('span');
  tagPill.className = 'tag-pill';
  tagPill.textContent = item.tag;
  meta.appendChild(tagPill);
  const ts = document.createElement('span');
  ts.className = 'timestamp';
  ts.textContent = relativeTime(item.published_at);
  meta.appendChild(ts);
  header.appendChild(meta);

  post.appendChild(header);

  const isTextPost = item.text_post;
  const hasCarousel = !isTextPost;

  if (hasCarousel) {
    const media = document.createElement('div');
    media.className = 'media';
    const track = document.createElement('div');
    track.className = 'carousel-track';
    item.panels.forEach(panel => {
      const panelEl = document.createElement('div');
      panelEl.className = 'panel';
      panelEl.appendChild(renderPanel(panel));
      track.appendChild(panelEl);
    });
    media.appendChild(track);

    if (item.panels.length > 1) {
      const dots = document.createElement('div');
      dots.className = 'dots';
      item.panels.forEach((_, i) => {
        const dot = document.createElement('span');
        dot.className = 'dot' + (i === 0 ? ' active' : '');
        dots.appendChild(dot);
      });
      media.appendChild(dots);

      track.addEventListener('scroll', () => {
        const idx = Math.round(track.scrollLeft / track.clientWidth);
        [...dots.children].forEach((d, i) => d.classList.toggle('active', i === idx));
      }, { passive: true });
    }

    post.appendChild(media);
  }

  const footer = document.createElement('div');
  footer.className = 'post-footer';
  const saveBtn = document.createElement('button');
  saveBtn.className = 'save-btn';
  saveBtn.setAttribute('aria-label', 'Save post');
  const outlineIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 3c-1.1 0-2 .9-2 2v16l8-5.333L20 21V5c0-1.1-.9-2-2-2H6z"/></svg>';
  const filledIcon = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 3c-1.1 0-2 .9-2 2v16l8-5.333L20 21V5c0-1.1-.9-2-2-2H6z"/></svg>';
  const setSaveIcon = () => { saveBtn.innerHTML = isSaved(item.id) ? filledIcon : outlineIcon; };
  setSaveIcon();
  saveBtn.addEventListener('click', () => {
    toggleSave({
      id: item.id,
      title: item.title,
      url: item.url,
      source: item.source,
      tag: item.tag,
      published_at: item.published_at,
      panels: item.panels,
      text_post: item.text_post,
      saved_at: new Date().toISOString(),
    });
    setSaveIcon();
    if (document.getElementById('saved-view').classList.contains('active')) {
      renderSavedView();
    }
  });
  footer.appendChild(saveBtn);
  post.appendChild(footer);

  const caption = document.createElement('div');
  caption.className = 'caption';
  if (isTextPost) {
    caption.textContent = item.panels[0].content;
  } else {
    const sourceSpan = document.createElement('span');
    sourceSpan.className = 'caption-source';
    sourceSpan.textContent = item.source;
    caption.appendChild(sourceSpan);
    const link = document.createElement('a');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = item.title;
    caption.appendChild(link);
  }
  post.appendChild(caption);

  return post;
}

function renderFeed() {
  const container = document.getElementById('feed-view');
  container.innerHTML = '';
  if (FEED_ITEMS.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'Nothing new since the last refresh.';
    container.appendChild(empty);
    return;
  }
  FEED_ITEMS.forEach(item => container.appendChild(buildCard(item)));
}

function renderSavedView() {
  const list = document.getElementById('saved-list');
  list.innerHTML = '';
  const saved = getSaved();
  if (saved.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'Nothing saved yet.';
    list.appendChild(empty);
    return;
  }
  saved.forEach(item => {
    const card = buildCard(item);
    const saveBtn = card.querySelector('.save-btn');
    saveBtn.addEventListener('click', () => renderSavedView());
    list.appendChild(card);
  });
}

document.getElementById('saved-toggle-btn').addEventListener('click', () => {
  document.getElementById('feed-view').classList.add('hidden');
  document.getElementById('saved-view').classList.add('active');
  renderSavedView();
});
document.getElementById('back-btn').addEventListener('click', () => {
  document.getElementById('saved-view').classList.remove('active');
  document.getElementById('feed-view').classList.remove('hidden');
});
document.getElementById('wordmark-btn').addEventListener('click', () => {
  document.getElementById('saved-view').classList.remove('active');
  document.getElementById('feed-view').classList.remove('hidden');
});

renderFeed();
"""


def main():
    panelized = load_json(PANELIZED_PATH, [])
    feed_items = build_feed_items(panelized)

    feed_json = json.dumps(feed_items, ensure_ascii=False).replace("</script>", "<\\/script>")
    html = PAGE_TEMPLATE.format(feed_json=feed_json, app_js=APP_JS)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"Rendered {len(feed_items)} item(s) to {out_path}")


if __name__ == "__main__":
    main()
