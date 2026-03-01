#!/bin/bash
# Run pipeline with 3 parallel workers, 500/day, commit every 100.
# Use with cron: 0 2 * * * cd /home/misha/Tattoo_artists && ./scripts/run_daily_parallel.sh
# Run from repo root.

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate

echo "🔄 Daily parallel run: 500 artists/day, 3 workers, commit every 100"
python3 packages/scraper/src/pipeline_main.py --workers 3 --batch-size 100
echo "✅ Done"
