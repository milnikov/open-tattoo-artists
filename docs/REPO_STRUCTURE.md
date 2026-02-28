# Open Tattoo Artists — Recommended GitHub Repo Structure

This structure keeps **metadata open in GitHub**, **images in Cloudflare R2**, and **user data in Supabase**.

## Folder layout

```
open-tattoo-artists/
  apps/
    web/                          # Next.js app (Vercel deploy)
      app/                        # App Router
      src/
      public/
      package.json
      next.config.js
      .env.example

  packages/
    schema/                       # JSON Schemas + validators (zod optional)
      artist.schema.json
      styles.schema.json
      index.schema.json
      README.md
    scraper/                      # Scraper & uploader (python)
      src/
      requirements.txt
      README.md
      config.example.yaml

  data/                           # Open metadata (source of truth)
    artists/                      # One file per artist
      <handle>.json
    styles/
      styles.json                 # Flat list of styles (canonical)
    indexes/                      # Generated; do not edit manually
      artists.compact.json
      search-index.json
      meta.json

  docs/
    PRD.md
    SCRAPER_R2_ARCHITECTURE.md
    DATA_MODEL.md
    MODERATION.md
    PRIVACY.md
    LICENSES.md

  supabase/
    schema.sql                    # DB schema + RLS policies
    README.md

  .github/
    ISSUE_TEMPLATE/
      add-artist.md
      report-problem.md
    workflows/
      validate-data.yml           # validates JSON against schema
      build-indexes.yml           # generates indexes after merge

  LICENSE
  README.md
```

## What goes where

### GitHub (public, versioned)
- `data/artists/*.json` — artist records
- `data/styles/styles.json` — canonical styles
- `data/indexes/*` — generated indexes for fast UI
- `packages/schema/*` — schemas used in CI validation

### Cloudflare R2 (binary)
- Artist images (thumb + full WEBP)

### Supabase (private user data)
- Users, favourites, contributions tracking

## Naming rules (recommended)
- **Artist ID = Instagram handle** (lowercased)
- Files: `data/artists/<handle>.json`
- Image keys in R2:
  - `artists/<handle>/thumb/<image_id>.webp`
  - `artists/<handle>/full/<image_id>.webp`

## Generated indexes (why)
To keep the web app fast, generate compact indexes from full artist JSON files:
- `artists.compact.json`: minimal fields for list + filtering
- `search-index.json`: normalized names for quick search
- `meta.json`: counts, build timestamp, schema version

## Contributor workflow
- Users submit via website → GitHub Issue created
- Maintainer reviews, scrapes/updates metadata, and commits to `data/`
- GitHub Actions validates data + builds indexes
- Vercel deploys automatically
