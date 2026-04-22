#!/bin/bash
# Daily unattended SIMILAR-only discovery with resume state.

set -euo pipefail
cd "$(dirname "$0")/.."

NO_GIT_ARG=0
for arg in "$@"; do
  if [ "$arg" = "--no-git" ]; then
    NO_GIT_ARG=1
  else
    echo "Unknown argument: $arg"
    echo "Usage: bash scripts/run_daily_discover_instagram_similar.sh [--no-git]"
    exit 1
  fi
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

DAY_SECONDS=$((24 * 3600))
STATE_FILE="packages/scraper/instagram_similar_state.json"
REPORT_FILE="packages/scraper/instagram_similar_report.json"

DELAY_SECONDS="${DELAY_SECONDS:-0.2}"
MAX_SIMILAR_REQUESTS="${MAX_SIMILAR_REQUESTS:-1600}"
NO_GIT="${NO_GIT:-0}"  # set NO_GIT=1 to disable auto-commit/push
if [ "$NO_GIT_ARG" = "1" ]; then
  NO_GIT=1
fi

if [ ! -f "$STATE_FILE" ]; then
  cat > "$STATE_FILE" <<'JSON'
{
  "next_seed_offset": 0,
  "completed": false
}
JSON
fi

while true; do
  run_start=$(date +%s)
  next_offset=$(python3 - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("packages/scraper/instagram_similar_state.json").read_text(encoding="utf-8"))
print(int(s.get("next_seed_offset", 0)))
PY
)
  completed=$(python3 - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("packages/scraper/instagram_similar_state.json").read_text(encoding="utf-8"))
print("1" if s.get("completed") else "0")
PY
)
  if [ "$completed" = "1" ]; then
    echo "✅ Similar discovery complete for all seeds."
    exit 0
  fi

  echo "🔄 Daily SIMILAR run (start_offset=${next_offset}, max_requests=${MAX_SIMILAR_REQUESTS}, started $(date))"
  set +e
  python3 packages/scraper/src/discover_instagram_similar.py \
    --start-seed-offset "$next_offset" \
    --max-similar-requests "$MAX_SIMILAR_REQUESTS" \
    --delay "$DELAY_SECONDS"
  exit_code=$?
  set -e
  if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 2 ]; then
    echo "❌ discover_instagram_similar.py failed with exit code $exit_code"
    exit "$exit_code"
  fi

  python3 packages/scraper/src/merge_instagram_graph_sources.py

  python3 - <<'PY'
import json
from pathlib import Path
report = json.loads(Path("packages/scraper/instagram_similar_report.json").read_text(encoding="utf-8"))
state = {
    "next_seed_offset": int(report.get("next_seed_offset", 0)),
    "completed": bool(report.get("all_seeds_processed", False)),
    "last_run": {
        "processed_seed_count": int(report.get("processed_seed_count", 0)),
        "similar_requests_made": int(report.get("similar_requests_made", 0)),
        "run_candidate_count": int(report.get("run_candidate_count", 0)),
    }
}
Path("packages/scraper/instagram_similar_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
print(json.dumps(state, indent=2))
PY

  if [ "$NO_GIT" != "1" ]; then
    if ! git diff --quiet -- \
      packages/scraper/instagram_similar_raw.json \
      packages/scraper/instagram_similar_all.json \
      packages/scraper/instagram_similar_report.json \
      packages/scraper/instagram_similar_state.json \
      packages/scraper/instagram_discovery_graph_all.json \
      packages/scraper/instagram_discovery_graph_raw.json \
      packages/scraper/instagram_discovery_report.json \
      packages/scraper/instagram_discovered_candidates.json; then
      git add \
        packages/scraper/instagram_similar_raw.json \
        packages/scraper/instagram_similar_all.json \
        packages/scraper/instagram_similar_report.json \
        packages/scraper/instagram_similar_state.json \
        packages/scraper/instagram_discovery_graph_all.json \
        packages/scraper/instagram_discovery_graph_raw.json \
        packages/scraper/instagram_discovery_report.json \
        packages/scraper/instagram_discovered_candidates.json
      if ! git diff --cached --quiet; then
        git commit -m "chore: save daily instagram similar discovery artifacts"
        if ! git push origin main; then
          echo "⚠️ Auto-push failed (remote ahead?). Commit is kept locally."
        fi
      fi
    fi
  fi

  if [ "$exit_code" -eq 2 ]; then
    echo "✅ All seeds processed for similar."
    exit 0
  fi

  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((DAY_SECONDS - elapsed))
  if [ "$sleep_sec" -gt 0 ]; then
    echo "⏸ Waiting ${sleep_sec}s (~$((sleep_sec / 3600))h) until next run..."
    sleep "$sleep_sec"
  fi
done
