#!/bin/bash
# Run pipeline with 3 parallel workers, 500/day, commit every 100.
# Loops: process 500 → wait until 24h since run start → process next 500 (keeps ~500/day).
# Run once in screen; no cron needed. Run from repo root.

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate

DAY_SECONDS=$((24 * 3600))

while true; do
  run_start=$(date +%s)
  echo "🔄 Daily parallel run: 500 artists/day, 3 workers, commit every 100 (started $(date))"
  python3 packages/scraper/src/pipeline_main.py --workers 3 --batch-size 100
  echo "✅ Batch done"

  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((DAY_SECONDS - elapsed))
  if [ "$sleep_sec" -gt 0 ]; then
    echo "⏸ Waiting ${sleep_sec}s (~$((sleep_sec / 3600))h) until next 500 (24h from batch start)..."
    sleep "$sleep_sec"
  fi
done
