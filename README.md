# Signal

A self-populating personal feed — Instagram's dark-mode visual language with
every social/engagement mechanic stripped out. Pulls from sources you trust,
refreshes on a schedule (default every 6 hours), and is otherwise inert: no
pull-to-refresh, no algorithmic ranking, no like/comment/share counts.

Full design rationale and constraints: see the original build spec this repo
was generated from.

## Pipeline

```
fetch.py -> dedupe.py -> panelize.py -> render.py
```

Each stage reads/writes a JSON file under `data/`; `render.py` produces the
final `docs/index.html`, served by GitHub Pages.

- `config/sources.yml` — the only file you touch to add/remove/retag a source.
  Tag must be one of the fixed set in `TAGS` (`scripts/common.py`): `news`,
  `financial`, `philosophy`, `engineering`, `fun`. Adding a new tag value
  here without adding it to `TAGS` also works (it still renders), it just
  won't get a guaranteed floor below.
- `data/seen.json` — committed between runs; used only to catch the same
  story being covered by a *different* source in a later cycle (e.g. NYT
  runs it this cycle, Reuters picks it up next cycle). It does **not** hide
  items just because they were already shown — an unopened item stays in
  the feed under the normal cap/rotation below, not disappear. Skipping a
  day should cost nothing.
- `docs/index.html` — generated. Do not hand-edit.

Each refresh caps display at 45 (`FEED_DISPLAY_CAP` in `scripts/common.py`)
— so what you see is always "the 45 most recent right now," recomputed
fresh each cycle, not a shrinking pool of unseen leftovers. Within that cap,
each tag (`TAGS` in `scripts/common.py`) is guaranteed `MIN_SLOTS_PER_TAG`
slots filled by its own most-recent items first, so low-frequency tags
(philosophy, engineering) aren't structurally locked out by high-frequency
ones (news, financial post many times a day). Remaining slots fill by pure
global recency across everything. Either constant can be tuned; the
mechanism is still a static, transparent rule, not engagement-based — the
final display order is always strict reverse-chronological regardless of
which phase picked an item.

## Local run

```bash
python -m venv .venv
.venv/Scripts/activate       # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python scripts/fetch.py
python scripts/dedupe.py
python scripts/panelize.py
python scripts/render.py
```

Then open `docs/index.html` directly, or serve it locally:

```bash
python -m http.server 8000 --directory docs
```

## Deploying

1. Push this repo to GitHub (public, for free-tier Pages).
2. Settings → Pages → deploy from the `docs/` folder on `main`.
3. Settings → Actions → General → Workflow permissions → "Read and write
   permissions" (needed so `refresh.yml` can commit the regenerated feed).
4. The `refresh.yml` workflow runs every 6 hours and on manual dispatch.

## Known TODOs (see `config/sources.yml`)

- **Prosblogion**: currently skipped (`feed_url: null`). The blog moved from
  `prosblogion.ektopos.com` (dead) to `prosblogion.com` after a 2018
  shutdown-and-revival; its `/feed/` couldn't be verified live from this dev
  sandbox (network-level security block) or via a second, off-network fetch
  path (got a JS-loading placeholder instead of XML either way). Needs a
  human check from an ordinary browser before adding a `feed_url`.
- **PhilPapers**: category-scoped via `?format=rss` on the category browse
  page (no login needed) — but PhilPapers' feed output never includes a
  per-item date, so these items always sort as "just published" each cycle
  (same as before this was Metaphysics-scoped; not a new limitation).
- **Reddit feeds**: the `.rss` endpoints are blocked by bot-detection from
  some networks/sandboxes — confirm they resolve from wherever this actually
  runs (they work fine from ordinary residential IPs and GitHub-hosted
  runners as of this writing).
