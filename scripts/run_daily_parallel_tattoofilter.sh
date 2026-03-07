#!/bin/bash
# Run TattooFilter pipeline with 3 parallel workers, ~500/day, commit every 100.
# Uses tattoofilter_new_artists.json and scrape_state_tattoofilter.json.
# Loops: process 500 → wait until 24h since run start → next 500. Run once in screen; no cron needed.
# Run from repo root.

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate
export PYTHONPATH="$(pwd)/packages/scraper/src${PYTHONPATH:+:$PYTHONPATH}"

DAY_SECONDS=$((24 * 3600))

while true; do
  run_start=$(date +%s)
  echo "🔄 TattooFilter daily parallel run: 500 artists/day, 3 workers, commit every 100 (started $(date))"
  python3 packages/scraper/src/pipeline_tattoofilter.py --workers 3 --batch-size 100
  exit_code=$?
  if [ "$exit_code" -eq 2 ]; then
    echo "✅ All TattooFilter artist pages processed. Exiting."
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
