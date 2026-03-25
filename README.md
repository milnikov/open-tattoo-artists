# Open Tattoo Artists

**Open-source tattoo artist directory** — metadata on GitHub, images on Cloudflare R2, web app for discovery and community contribution.

- **Web app**: Browse artists, filter by location/style, search, save favourites, suggest artists, report problems. Next.js in `apps/web`.
- **Open data**: Artist JSON in `data/artists/`, styles in `data/styles/`, generated indexes in `data/indexes/`.
- **Docs**: [docs/README.md](docs/README.md) — PRD, data model, setup/deploy, VM commands, licenses.

---

## Quick start

### Web app (local)

```bash
cd apps/web
cp .env.example .env.local   # add Supabase + R2 URLs, see apps/web/.env.example
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). See [docs/GOOGLE_AUTH_SETUP.md](docs/GOOGLE_AUTH_SETUP.md) for Sign in with Google.

---

## Project structure

| Path | Purpose |
|------|---------|
| `apps/web/` | Next.js app (browse, filters, search, favourites, suggest, report) |
| `packages/schema/` | JSON schemas for artist data |
| `packages/scraper/` | Python scraper, R2 upload, `config.example.yaml` |
| `data/artists/` | One JSON file per artist (source of truth) |
| `data/styles/` | Canonical style list |
| `data/indexes/` | Generated indexes (do not edit by hand) |
| `docs/` | PRD, setup/deploy, VM command reference, licenses |
| `supabase/` | DB schema (auth, favourites, contributions) |
| `.github/` | Issue templates, CI workflows |

---

## Contributing

- **Suggest an artist** or **Report a problem** via the web app (creates a GitHub Issue).
- Issue templates: [.github/ISSUE_TEMPLATE/add-artist.md](.github/ISSUE_TEMPLATE/add-artist.md), [.github/ISSUE_TEMPLATE/report-problem.md](.github/ISSUE_TEMPLATE/report-problem.md).
- See [docs/MODERATION.md](docs/MODERATION.md) for how submissions are reviewed.

---

## License

- **Code**: MIT  
- **Structured data**: CC BY 4.0 (attribution required)  
- **Tattoo images**: Not owned by this project; used for directory purposes. See [docs/LICENSES.md](docs/LICENSES.md).

---

## GitHub About (repo settings)

Suggested **Description** for the repo About section:

```
Open-source tattoo artist directory — web app and open data (GitHub + R2). Browse, filter, search, suggest artists, report problems.
```

Suggested **Topics**: `tattoo`, `directory`, `open-data`, `nextjs`, `supabase`, `cloudflare-r2`, `open-source`.

Optional **Website**: your deployed app URL (e.g. Vercel).
