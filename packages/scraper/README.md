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

## Requirements
- Python 3.10+
- Chrome/Chromium for Selenium
- See `requirements.txt`

## Docs
- [SCRAPER_R2_ARCHITECTURE.md](../../docs/SCRAPER_R2_ARCHITECTURE.md) — flow, R2 keys, image variants
