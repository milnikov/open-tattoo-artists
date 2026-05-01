#!/bin/bash
# Continuous phase-2 loop:
# 1) merge latest split raw graph data into one candidate list
# 2) probe each candidate (1 stable-API call: bio + stats), cached
# 3) score with tattoo_confidence and create artist JSONs only for survivors
# 4) heavy enrich (following list + 30 posts + R2) for newly created artists
# 5) rebuild indexes
# 6) commit/push, sleep, repeat

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
PROBE_LIMIT="${PROBE_LIMIT:-}"
AUTO_CREATE_LIMIT="${AUTO_CREATE_LIMIT:-}"
AUTO_CREATE_THRESHOLD="${AUTO_CREATE_THRESHOLD:-0.75}"
MIN_FOLLOWERS="${MIN_FOLLOWERS:-3000}"
REQUIRE_PROBE="${REQUIRE_PROBE:-1}"
ENRICH_DELAY="${ENRICH_DELAY:-1.0}"
ENRICH_BATCH_SIZE="${ENRICH_BATCH_SIZE:-100}"
LOOP_SLEEP_SECONDS="${LOOP_SLEEP_SECONDS:-1800}"
NO_GIT="${NO_GIT:-0}"
if [ "$NO_GIT_ARG" = "1" ]; then
  NO_GIT=1
fi

CREATE_LIMIT_ARGS=()
if [ -n "$AUTO_CREATE_LIMIT" ]; then
  CREATE_LIMIT_ARGS+=(--limit "$AUTO_CREATE_LIMIT")
fi

PROBE_LIMIT_ARGS=()
if [ -n "$PROBE_LIMIT" ]; then
  PROBE_LIMIT_ARGS+=(--limit "$PROBE_LIMIT")
fi

REQUIRE_PROBE_ARGS=()
if [ "$REQUIRE_PROBE" = "1" ]; then
  REQUIRE_PROBE_ARGS+=(--require-probe)
fi

ENRICH_GIT_ARGS=()
if [ "$NO_GIT" = "1" ]; then
  ENRICH_GIT_ARGS+=(--no-git)
fi

while true; do
  run_start=$(date +%s)
  echo "🔄 Phase-2 cycle started $(date)"

  echo "1/5 Merge split graph sources + refresh legacy candidate files"
  python3 packages/scraper/src/merge_instagram_graph_sources.py --min-evidence "$MIN_EVIDENCE"

  echo "2/5 Probe candidates (bio + stats; cached)"
  python3 packages/scraper/src/probe_discovery_candidates.py "${PROBE_LIMIT_ARGS[@]}"

  echo "3/5 Score and create artist JSONs (threshold=${AUTO_CREATE_THRESHOLD}, min_followers=${MIN_FOLLOWERS})"
  python3 packages/scraper/src/create_artists_from_discovery_candidates.py \
    --auto-create-threshold "$AUTO_CREATE_THRESHOLD" \
    --min-followers "$MIN_FOLLOWERS" \
    "${REQUIRE_PROBE_ARGS[@]}" \
    "${CREATE_LIMIT_ARGS[@]}"

  CREATED_IDS_FILE="packages/scraper/instagram_discovery_created_ids.txt"
  if [ -s "$CREATED_IDS_FILE" ]; then
    echo "4/5 Enrich newly created artists (batch-size=${ENRICH_BATCH_SIZE})"
    # Enrich exits 2 ("all done") when every id in the file is already enriched,
    # which is a normal steady-state outcome and must not crash the loop.
    set +e
    python3 packages/scraper/src/enrich_instagram_rapidapi.py \
      --only-ids-file "$CREATED_IDS_FILE" \
      --delay "$ENRICH_DELAY" \
      --batch-size "$ENRICH_BATCH_SIZE" \
      "${ENRICH_GIT_ARGS[@]}"
    enrich_exit=$?
    set -e
    if [ "$enrich_exit" -ne 0 ] && [ "$enrich_exit" -ne 2 ]; then
      echo "❌ Enrich failed with exit code $enrich_exit"
      exit "$enrich_exit"
    fi
  else
    echo "4/5 No new artists passed the gate this cycle."
  fi

  echo "5/5 Rebuild indexes"
  python3 scripts/build_indexes.py

  if [ "$NO_GIT" != "1" ]; then
    if ! git diff --quiet -- \
      data/artists \
      data/indexes/artists.compact.json \
      data/indexes/meta.json \
      packages/scraper/instagram_discovered_candidates.json \
      packages/scraper/instagram_discovered_candidates_probed.json \
      packages/scraper/instagram_discovery_graph_raw.json \
      packages/scraper/instagram_discovery_report.json \
      packages/scraper/instagram_discovery_graph_all.json \
      packages/scraper/instagram_discovery_created_ids.txt \
      packages/scraper/instagram_discovery_rejected.json; then
      git add \
        data/artists \
        data/indexes/artists.compact.json \
        data/indexes/meta.json \
        packages/scraper/instagram_discovered_candidates.json \
        packages/scraper/instagram_discovered_candidates_probed.json \
        packages/scraper/instagram_discovery_graph_raw.json \
        packages/scraper/instagram_discovery_report.json \
        packages/scraper/instagram_discovery_graph_all.json \
        packages/scraper/instagram_discovery_created_ids.txt \
        packages/scraper/instagram_discovery_rejected.json
      if ! git diff --cached --quiet; then
        git commit -m "chore: save phase2 discovery create+enrich artifacts"
        if ! git push origin main; then
          echo "⚠️ Auto-push failed (remote ahead?). Commit is kept locally."
        fi
      fi
    fi
  fi

  echo "✅ Cycle done."
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
