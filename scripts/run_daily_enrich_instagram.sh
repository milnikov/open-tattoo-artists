#!/bin/bash
# Enrich data/artists with Instagram API (user_data, user_posts, following).
# Loops: process --limit artists → wait until 24h since run start → next batch. Exit when all done.
# Run once in screen; no cron needed. Run from repo root.
# Set RAPIDAPI_KEY in the environment (or export in this script / .env).

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate

if [ -z "${RAPIDAPI_KEY}" ]; then
  echo "❌ RAPIDAPI_KEY not set. Export it or add to this script."
  exit 1
fi

DAY_SECONDS=$((24 * 3600))
# Artists per run; commit every 100 (like pipeline)
LIMIT=500
BATCH_SIZE=100

while true; do
  run_start=$(date +%s)
  echo "🔄 Enrich Instagram: ${LIMIT} artists/run, commit every ${BATCH_SIZE} (started $(date))"
  python3 packages/scraper/src/enrich_instagram_rapidapi.py --limit "$LIMIT" --batch-size "$BATCH_SIZE"
  exit_code=$?
  if [ "$exit_code" -eq 2 ]; then
    echo "✅ All artists enriched. Exiting."
    exit 0
  fi
  if [ "$exit_code" -ne 0 ]; then
    echo "❌ Enrich failed with exit code $exit_code"
    exit "$exit_code"
  fi
  echo "✅ Batch done"

  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((DAY_SECONDS - elapsed))
  if [ "$sleep_sec" -gt 0 ]; then
    echo "⏸ Waiting ${sleep_sec}s (~$((sleep_sec / 3600))h) until next run (24h from batch start)..."
    sleep "$sleep_sec"
  fi
done
