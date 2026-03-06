# Scraper → Cloudflare R2 Upload Architecture

This doc describes how to scrape artist pages (e.g., TattoosWizard) and store:
- **Open metadata** in GitHub (`data/`)
- **Images** in Cloudflare R2 (`artists/<handle>/...`)

## Objectives
- Be resumable (crashes don’t lose progress)
- Be polite (rate-limited, retries, backoff)
- Store optimized images (WEBP, thumb + full)
- Keep stable identifiers (artist ID = Instagram handle)

---

## High-level flow

1) **Input**
- A list of artist page URLs (e.g., ~19k TattoosWizard links)

2) **Fetch + parse**
- Download artist page HTML
- Extract:
  - Instagram URL + handle (required)
  - Name (fallback to handle)
  - Location (city/country)
  - Styles (if present)
  - Outbound links (website/studio/booking)
  - Image URLs (portfolio)

3) **Normalize**
- `artist_id = instagram_handle.lower()`
- Cap images to **50** for MVP (keep most recent/top by page order)

4) **Download images**
- Use concurrency, but keep it sane:
  - Example: 5–15 concurrent downloads
- Retry logic:
  - 3 retries
  - exponential backoff (1s, 3s, 9s)
- Validate downloads (file size > 0)

5) **Transform**
- Convert to WEBP
- Create two variants:
  - `thumb` (e.g., 400px wide)
  - `full` (e.g., 1600–2000px wide)
- Recommended: strip EXIF metadata

6) **Upload to R2**
- For each image:
  - `artists/<handle>/thumb/<image_id>.webp`
  - `artists/<handle>/full/<image_id>.webp`
- Set cache headers:
  - `Cache-Control: public, max-age=31536000, immutable`

7) **Write artist JSON**
- Create/update `data/artists/<handle>.json`
- Populate:
  - `tattoos[]` with `image_id`, `image_full`, `image_thumb`
  - `analysis` fields present but empty initially

8) **Commit metadata**
- Commit in batches (e.g., every 50–200 artists) to reduce Git overhead
- Push to a branch and open a PR (recommended), or commit directly if you control repo

---

## R2 configuration

### Recommended
- R2 bucket: `open-tattoo-artists`
- Public access via Cloudflare:
  - Use a custom domain like: `https://img.<your-domain>/`
- Ensure CORS allows GET from your web domain.

### Key conventions
- Do **not** store source filenames (often messy).
- Use stable incremental IDs per artist:
  - `001.webp`, `002.webp`, ...
- This makes dedupe and diffing easy.

---

## Data quality rules

### Required to create an artist record
- Instagram URL AND handle

### If location is missing
- Save as:
  - city: `"Unknown"`
  - country: `"Unknown"`
…and allow later community fixes via Report Problem issues.

### Styles
- Store style slugs (flat list).
- If scraper extracts unknown styles, keep them but flag later for cleanup.

---

## Resumability

Maintain a local state file (or SQLite) on VPS:
- `scrape_state.json`:
  - list of completed artist_ids
  - last processed URL index
- Before processing a URL:
  - if `artist_id` already exists in GitHub data → skip
  - if images exist in R2 for that artist → optionally skip or reconcile

---

## Rate limiting & safety
- Add a random jitter between requests (e.g., 200–600ms)
- Respect remote server response codes
- Backoff on 429/503

---

## Output artifacts

### GitHub (open metadata)
- `data/artists/<handle>.json`

### R2 (images)
- `artists/<handle>/thumb/*.webp`
- `artists/<handle>/full/*.webp`

---

## Suggested Python module breakdown

- `fetch.py` — HTTP client, retries, rate limiting
- `parse.py` — HTML parsing, extraction
- `images.py` — download + WEBP conversion + resizing
- `r2.py` — S3-compatible uploads to R2
- `writer.py` — JSON writer + schema_version stamping
- `state.py` — resume state tracking
- `main.py` — orchestration

Actual entrypoints and layout: see `packages/scraper/src/` (e.g. `pipeline_main.py`).

---

## Future: CV enrichment pipeline (separate job)
- Run a batch worker that reads image keys from GitHub data
- Produces AI tags:
  - themes, dominant_colours, body_parts, size_category, confidence_score
- Write results back either:
  - into GitHub via PR, or
  - into Supabase `tattoo_analysis` table (recommended for fast iteration)

