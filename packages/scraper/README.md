# Scraper & uploader (Python)

Scrapes artist pages (e.g. Tattoodo, TattoosWizard), normalizes metadata, and can upload images to Cloudflare R2.

## Layout
- `src/` — Python scripts (discovery, download, batch process). All paths are relative to **repo root**.
- `config.example.yaml` — copy to `config.yaml` and set R2/source options

## Running
Always run from **repo root**. The scraper reads the artist list from `packages/scraper/discovered_pages.json` (and writes discovery output here or under `TATTOODO/`). Other paths (`data/cities/`, `artists_examples/`) are relative to repo root.

```bash
# From repo root
python packages/scraper/src/pipeline_main.py          # tattooswizard: parse -> download -> R2 -> data/artists
python packages/scraper/src/batch_process_artists.py
python packages/scraper/src/discover_tattoodo.py
# etc.
```

### VPS / rate limits
On a VPS, the pipeline runs **sequentially**: one artist page → parse (Selenium) → download images → R2 upload → write JSON → delay (3–12s + extra every 10) → next. It **resumes** from `packages/scraper/scrape_state.json` (`last_index` + `completed_ids`), so each run continues where the previous stopped.

- **Without a cap**, a single run would process the entire remaining list (~19k URLs) and exceed a safe daily request volume.
- Set **`max_artists_per_run: 500`** in `config.yaml` (or pass `--limit 500`) so each run processes at most 500 artists. Run **once per day** (e.g. cron at 02:00): that stays within ~400–600 pages/day and fits the limit. `--limit` overrides the config cap if you need a one-off different batch size.

## Hidden artists → Instagram enrichment

Artists hidden on the website (see PRD visibility rules) are listed for batch enrichment in **`packages/scraper/hidden_artist_ids.json`** (JSON array of `id` strings; only entries with `links.instagram`). Regenerate from current `data/indexes/artists.compact.json` and `data/indexes/countries.json`:

```bash
python3 packages/scraper/src/list_hidden_artists.py
```

Then run `enrich_instagram_rapidapi.py --only-ids-file packages/scraper/hidden_artist_ids.json` (see [VM_AND_GIT_COMMANDS.md](../../docs/VM_AND_GIT_COMMANDS.md)).

## Requirements
- Python 3.10+
- Chrome/Chromium for Selenium
- See `requirements.txt`

## Docs
- [SETUP_AND_DEPLOY.md](../../docs/SETUP_AND_DEPLOY.md) — R2 + VPS + deploy overview  
- [VM_AND_GIT_COMMANDS.md](../../docs/VM_AND_GIT_COMMANDS.md) — VM command cheat sheet
