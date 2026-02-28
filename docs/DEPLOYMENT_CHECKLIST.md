# Deployment Checklist

## Steps 1–4 ✓ (You’ve done these)

1. Create R2 bucket, copy Account ID, create API token  
2. `cp config.example.yaml config.yaml` and fill R2 credentials  
3. Run `python3 packages/scraper/src/pipeline_main.py --limit 2`  
4. Verify objects in the R2 bucket  

---

## Step 5: Add NEXT_PUBLIC_IMAGES_BASE_URL ✓

Already configured in `apps/web/.env.local`:

```
NEXT_PUBLIC_IMAGES_BASE_URL=https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev
```

This is your R2 public URL from `config.yaml`. For other deployments (e.g. Vercel), set the same env var in your hosting dashboard.

---

## Step 6: Deploy to VPS and run the full pipeline

### 6a. Deploy the Next.js app

**Option A: Vercel (recommended)**

1. Push your repo to GitHub  
2. Import the project in [Vercel](https://vercel.com)  
3. **Set Root Directory**: Project Settings → General → Root Directory → `apps/web` (required — the Next.js app lives there)  
4. **Data**: The build copies `data/` into the app automatically. Ensure `data/artists/*.json` exist and run `python3 scripts/build_indexes.py` from repo root, then commit `data/indexes/*.json` so the directory shows artists.  
5. Set environment variables:
   - `NEXT_PUBLIC_IMAGES_BASE_URL` = `https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev`
   - Optional: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`  
6. Deploy (build command: `npm run build` — it runs `copy-data.js` then `next build`)

**Option B: Same VPS as the pipeline**

```bash
# On your VPS (after clone)
cd Tattoo_artists
npm install
cd apps/web
npm run build
# Run with PM2 or systemd (example with PM2):
npm install -g pm2
NEXT_PUBLIC_IMAGES_BASE_URL=https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev pm2 start npm --name "tattoo-web" -- start
pm2 save && pm2 startup
```

### 6b. Run the full pipeline on the VPS

Follow [VM_SETUP_GUIDE.md](./VM_SETUP_GUIDE.md) to:

1. Clone repo on the VPS  
2. Run `./scripts/setup_vm.sh`  
3. Configure `packages/scraper/config.yaml` (copy your R2 credentials)  
4. Run the pipeline (e.g. in `screen` or `tmux`):

```bash
cd Tattoo_artists
source venv/bin/activate
python3 packages/scraper/src/pipeline_main.py
```

To cap each run (e.g. 500 artists) and run daily:

```bash
python3 packages/scraper/src/pipeline_main.py --limit 500
```

Progress is saved in `packages/scraper/scrape_state.json`. Each run resumes from the last index.

### 6c. Sync data to your web app

If the web app runs separately from the VPS:

- R2 images are already public at `https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev`  
- Artist JSON is in `data/artists/*.json`. Either:
  - Build the index locally and commit (`scripts/build_indexes.py`), then deploy the app, or  
  - Copy `data/artists/` to your deployment and run `build_indexes.py` there
