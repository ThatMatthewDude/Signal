# Atlas

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
  runs it this cycle, BBC picks it up next cycle). It does **not** hide
  items just because they were already shown — an unopened item stays in
  the feed under the normal cap/rotation below, not disappear. Skipping a
  day should cost nothing.
- `docs/index.html` — generated. Do not hand-edit.

### Live / Weekly tabs

The rendered page is two independently-scrolling, independently-capped
feeds, not one mixed pool - a fast-posting source (a subreddit, a wire-style
news feed) would otherwise permanently outpost a source that posts a few
times a week under any shared reverse-chron ranking, no matter how the
slots are divided. Each source in `sources.yml` has a `cadence: live` or
`cadence: weekly`, measured from its own actual posting history (see the
comment block at the top of `sources.yml` for the method and the specific
per-source notes for the few that were genuinely hard to measure) — not
guessed from reputation.

Within *each* tab independently:

- Caps display at 45 (`FEED_DISPLAY_CAP` in `scripts/common.py`) — so what
  you see is always "the 45 most recent right now" for that tab, recomputed
  fresh each cycle, not a shrinking pool of unseen leftovers.
- Each tag (`TAGS` in `scripts/common.py`) is guaranteed `MIN_SLOTS_PER_TAG`
  slots filled by its own most-recent items first, so a low-frequency tag
  within that tab isn't structurally locked out by a high-frequency one.
  Remaining slots fill by pure global recency across everything in the tab.
- Within a tag, no single source can contribute more than
  `MAX_PER_SOURCE_PER_TAG` items (`scripts/common.py`) — the same crowding
  problem the tag floor solves one level up (a fast tag squeezing out a slow
  one) can otherwise recur one level down (a fast *source* squeezing out
  other sources sharing its tag — a high-volume subreddit, or an aggregator
  feed covering many authors/papers under one source entry). The cap applies
  during selection itself, in both the floor phase and the open recency
  fill, not as a post-hoc filter.

All three constants are tunable; the mechanism is still a static,
transparent rule, not engagement-based, and the tag floor and per-source cap
are both safety nets *within* a tab, not a substitute for the tab split —
the split is what actually separates the two paces. Final display order
within a tab is always strict reverse-chronological regardless of which
phase (floor or open pool) picked an item. Tag badges on individual cards
are unaffected either way; the tabs are top-level navigation only.

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
- **arXiv**: querying `cat:astro-ph` (the old pre-2009 umbrella category)
  with `sortBy=submittedDate&sortOrder=descending` returns genuinely ancient
  papers (2008, 2019) instead of recent ones; `physics.space-ph` and `cs.RO`
  sort correctly. Doesn't corrupt the feed (those items never rank high
  enough to show) but wastes fetch/API budget. Worth swapping `astro-ph` for
  a modern sub-category (e.g. `astro-ph.EP`) at some point.
- **Apricitas Economics**: hasn't published anything in ~3 months as of
  2026-08-04 per its own feed (last item from May) — still tagged `weekly`
  since that's genuinely its historical cadence, but it may just be dormant
  rather than actively weekly right now. Not a pipeline issue either way.
