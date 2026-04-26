#!/bin/bash
# Continuous phase-2 loop:
# 1) merge latest split raw graph data
# 2) refresh legacy candidates from merged data
# 3) create new artist JSONs from candidates
# 4) enrich only newly created artists
# 5) rebuild indexes
# 6) sleep and repeat

set -euo pipefail
cd "$(dirname "$0")/.."

NO_GIT_ARG=0
ONCE=0
for arg in "$@"; do
  case "$arg" in
    --no-git) NO_GIT_ARG=1 ;;
    --once) ONCE=1 ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: bash scripts/run_discovery_create_and_enrich.sh [--no-git] [--once]"
      exit 1
      ;;
  esac
done

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

if [ -z "${RAPIDAPI_KEY:-}" ]; then
  echo "RAPIDAPI_KEY is not set."
  exit 1
fi

MIN_EVIDENCE="${MIN_EVIDENCE:-2}"
AUTO_CREATE_LIMIT="${AUTO_CREATE_LIMIT:-}"
ENRICH_DELAY="${ENRICH_DELAY:-1.0}"
LOOP_SLEEP_SECONDS="${LOOP_SLEEP_SECONDS:-1800}"
NO_GIT="${NO_GIT:-0}"
if [ "$NO_GIT_ARG" = "1" ]; then
  NO_GIT=1
fi

LIMIT_ARGS=()
if [ -n "$AUTO_CREATE_LIMIT" ]; then
  LIMIT_ARGS+=(--limit "$AUTO_CREATE_LIMIT")
fi

while true; do
  run_start=$(date +%s)
  echo "🔄 Phase-2 cycle started $(date)"
  echo "1/5 Merge split graph sources + refresh legacy candidate files"
  python3 packages/scraper/src/merge_instagram_graph_sources.py --min-evidence "$MIN_EVIDENCE"

  echo "2/5 Create artist JSONs from candidates"
  python3 packages/scraper/src/create_artists_from_discovery_candidates.py "${LIMIT_ARGS[@]}"

  CREATED_IDS_FILE="packages/scraper/instagram_discovery_created_ids.txt"
  if [ -s "$CREATED_IDS_FILE" ]; then
    echo "3/5 Enrich newly created artists"
    # Enrich exits 2 ("all done") when every id in the file is already enriched,
    # which is a normal steady-state outcome and must not crash the loop.
    set +e
    python3 packages/scraper/src/enrich_instagram_rapidapi.py \
      --only-ids-file "$CREATED_IDS_FILE" \
      --delay "$ENRICH_DELAY"
    enrich_exit=$?
    set -e
    if [ "$enrich_exit" -ne 0 ] && [ "$enrich_exit" -ne 2 ]; then
      echo "❌ Enrich failed with exit code $enrich_exit"
      exit "$enrich_exit"
    fi
  else
    echo "3/5 No new artists created in this cycle."
  fi

  echo "4/5 Rebuild indexes"
  python3 scripts/build_indexes.py

  if [ "$NO_GIT" != "1" ]; then
    if ! git diff --quiet -- \
      data/artists \
      data/indexes/artists.compact.json \
      data/indexes/meta.json \
      packages/scraper/instagram_discovered_candidates.json \
      packages/scraper/instagram_discovery_graph_raw.json \
      packages/scraper/instagram_discovery_report.json \
      packages/scraper/instagram_discovery_graph_all.json \
      packages/scraper/instagram_discovery_created_ids.txt; then
      git add \
        data/artists \
        data/indexes/artists.compact.json \
        data/indexes/meta.json \
        packages/scraper/instagram_discovered_candidates.json \
        packages/scraper/instagram_discovery_graph_raw.json \
        packages/scraper/instagram_discovery_report.json \
        packages/scraper/instagram_discovery_graph_all.json \
        packages/scraper/instagram_discovery_created_ids.txt
      if ! git diff --cached --quiet; then
        git commit -m "chore: save phase2 discovery create+enrich artifacts"
        if ! git push origin main; then
          echo "⚠️ Auto-push failed (remote ahead?). Commit is kept locally."
        fi
      fi
    fi
  fi

  echo "5/5 Cycle done."
  if [ "$ONCE" = "1" ]; then
    exit 0
  fi
  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((LOOP_SLEEP_SECONDS - elapsed))
  if [ "$sleep_sec" -lt 10 ]; then
    sleep_sec=10
  fi
  echo "⏸ Waiting ${sleep_sec}s before next phase-2 cycle..."
  sleep "$sleep_sec"
done
