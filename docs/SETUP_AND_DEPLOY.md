# Setup and deploy (VPS + web)

**Day-to-day commands** (pipelines, git, screen, TattooFilter, enrich): use **[VM_AND_GIT_COMMANDS.md](./VM_AND_GIT_COMMANDS.md)** — this file is first-time setup, deploy, and how the pieces fit together.

## What you are running

- **Metadata:** `data/artists/<handle>.json` in Git.  
- **Images:** Cloudflare R2 at `artists/<handle>/thumb|full/<id>.webp`.  
- **Entrypoint:** `packages/scraper/src/pipeline_main.py` (resumes via `packages/scraper/scrape_state.json`).  
- **Legacy:** `batch_process_artists.py` saves local JPGs; progress in `batch_progress.json`.

Pipeline flow (conceptually): fetch page → parse (Selenium/headless) → download → WEBP thumb+full → upload R2 → write JSON → optional git batch. Details: `packages/scraper/README.md`.

---

## First-time VPS (Ubuntu)

From **repo root** on the server.

1. **Clone** — `git clone <repo-url> Tattoo_artists && cd Tattoo_artists`  
2. **Bootstrap** — `chmod +x scripts/setup_vm.sh && ./scripts/setup_vm.sh` (~5–10 min). Creates **`venv/`** and installs root `requirements.txt`.  
3. **R2** — `cp packages/scraper/config.example.yaml packages/scraper/config.yaml` and fill `r2:` (or `scp` from your laptop).  
4. **Git on VM** (if the pipeline pushes) — `git config user.name` / `user.email`; SSH key or HTTPS token.  
5. **Smoke test** — `source venv/bin/activate`, then:
   - `python3 packages/scraper/src/pipeline_main.py --limit 2 --no-r2`
   - `python3 packages/scraper/src/pipeline_main.py --limit 2` (needs R2)

**Production:** `./scripts/run_daily_parallel.sh` in `screen` — see VM_AND_GIT_COMMANDS.

**Troubleshooting:** Chrome/driver (`google-chrome --version`, `webdriver-manager`); OOM → smaller batches/workers; `pip install` inside `venv`. Throughput ballpark **~10–30 s/artist**.

---

## R2 + pipeline before the VPS

1. R2 bucket + API token  
2. `config.yaml` from `config.example.yaml`  
3. `python3 packages/scraper/src/pipeline_main.py --limit 2`  
4. Confirm bucket objects and `data/artists/*.json`

---

## Web app environment

**`NEXT_PUBLIC_IMAGES_BASE_URL`** must match **`r2.public_url`** in `packages/scraper/config.yaml` (e.g. `apps/web/.env.local` and production host env).

**Deploy Next.js**

- **Vercel:** Import repo → **Root Directory** `apps/web` → env vars (`NEXT_PUBLIC_IMAGES_BASE_URL`, Supabase if used) → deploy.  
- **Same host as scraper:** `cd apps/web && npm ci && npm run build`; run with `pm2` / `systemd`; same env vars.

**Indexes:** If the build needs generated lists, run `scripts/build_indexes.py` where `data/artists/` is present, then deploy or commit per your workflow.

---

## Sign in with Google

[GOOGLE_AUTH_SETUP.md](./GOOGLE_AUTH_SETUP.md)

---

## Scraper behavior notes

- **VM/headless:** Chrome runs headless with stable flags and **`webdriver-manager`** for drivers (replaces older “visible browser only” workflows).  
- **Scrolling / throttling:** Page scrolling continues until image count stabilizes (with a max scroll cap); requests use jitter, backoff on 429/5xx, and optional user-agent rotation — see `packages/scraper` source for tunables.
