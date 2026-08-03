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
- `data/seen.json` — committed between runs; tracks what's already been shown
  so the feed only ever surfaces genuinely new items (bounded, not an archive).
- `docs/index.html` — generated. Do not hand-edit.

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

- **PhilPapers**: shipped with the general new-papers feed; a
  Metaphysics-only feed requires manually generating a "Monitor this page"
  URL from a logged-in PhilPapers session.
- **3:16am**: no RSS exists on the source site; currently skipped
  (`feed_url: null`). Consider a third-party page-to-feed generator.
- **Reddit feeds**: the `.rss` endpoints are blocked by bot-detection from
  some networks/sandboxes — confirm they resolve from wherever this actually
  runs (they work fine from ordinary residential IPs and GitHub-hosted
  runners as of this writing).
