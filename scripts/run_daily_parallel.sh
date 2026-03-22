#!/bin/bash
# Run pipeline with 3 parallel workers, 500/day, commit every 500 (one push per daily batch).
# Loops: process 500 → wait until 24h since run start → process next 500 (keeps ~500/day).
# Run once in screen; no cron needed. Run from repo root:
#   bash scripts/run_daily_parallel.sh

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate

DAY_SECONDS=$((24 * 3600))

while true; do
  run_start=$(date +%s)
  echo "🔄 Daily parallel run: 500 artists/day, 3 workers, commit every 500 (started $(date))"
  python3 packages/scraper/src/pipeline_main.py --workers 3 --batch-size 500
  exit_code=$?
  if [ "$exit_code" -eq 2 ]; then
    echo "✅ All artist pages processed. Exiting."
    exit 0
  fi
  if [ "$exit_code" -ne 0 ]; then
    echo "❌ Pipeline failed with exit code $exit_code"
    exit "$exit_code"
  fi
  echo "✅ Batch done"

  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((DAY_SECONDS - elapsed))
  if [ "$sleep_sec" -gt 0 ]; then
    echo "⏸ Waiting ${sleep_sec}s (~$((sleep_sec / 3600))h) until next 500 (24h from batch start)..."
    sleep "$sleep_sec"
  fi
done
