# Docs

| Doc | Purpose |
|-----|---------|
| [PRD.md](./PRD.md) | Product requirements (MVP, visibility rules) |
| [DATA_MODEL.md](./DATA_MODEL.md) | Artist JSON + R2 paths |
| [SETUP_AND_DEPLOY.md](./SETUP_AND_DEPLOY.md) | VPS first-time setup, R2, Next.js deploy, how the pipeline fits together |
| [VM_AND_GIT_COMMANDS.md](./VM_AND_GIT_COMMANDS.md) | Command cheat sheet for the VM (pipelines, git, screen) |
| [GOOGLE_AUTH_SETUP.md](./GOOGLE_AUTH_SETUP.md) | Google + Supabase + web env |
| [MODERATION.md](./MODERATION.md) | Issue-based submissions |
| [PRIVACY.md](./PRIVACY.md) | What is stored where |
| [LICENSES.md](./LICENSES.md) | Code, data, images |
| [POST_MVP_PLAN.md](./POST_MVP_PLAN.md) | Future ideas |
| [VALIDATION_REPORT.md](./VALIDATION_REPORT.md) | One-off styles/location audit (historical) |

Schemas: `packages/schema/`. Supabase: `supabase/`. Scraper details: `packages/scraper/README.md`.

**Hidden-artist Instagram batch:** `packages/scraper/hidden_artist_ids.json` (in git) lists artist IDs hidden on the site that have Instagram, for `enrich_instagram_rapidapi.py --only-ids-file`. Regenerate with `python3 packages/scraper/src/list_hidden_artists.py` after index or visibility changes.

The `archive/` folder holds older copies; prefer the files above.
