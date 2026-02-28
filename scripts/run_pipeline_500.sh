#!/bin/bash
# Run pipeline: 500 artists per day. Resumes from scrape_state.json automatically.
# Use with cron: 0 3 * * * /home/misha/Tattoo_artists/scripts/run_pipeline_500.sh >> /home/misha/Tattoo_artists/pipeline.log 2>&1

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
source venv/bin/activate
exec python3 packages/scraper/src/pipeline_main.py --limit 500
