#!/bin/bash
# Daily unattended FOLLOWING-only discovery with resume state.

set -euo pipefail
cd "$(dirname "$0")/.."

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
STATE_FILE="packages/scraper/instagram_following_state.json"
REPORT_FILE="packages/scraper/instagram_following_report.json"

DELAY_SECONDS="${DELAY_SECONDS:-1.2}"
MAX_FOLLOWING_REQUESTS="${MAX_FOLLOWING_REQUESTS:-1400}"

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
s = json.loads(Path("packages/scraper/instagram_following_state.json").read_text(encoding="utf-8"))
print(int(s.get("next_seed_offset", 0)))
PY
)
  completed=$(python3 - <<'PY'
import json
from pathlib import Path
s = json.loads(Path("packages/scraper/instagram_following_state.json").read_text(encoding="utf-8"))
print("1" if s.get("completed") else "0")
PY
)
  if [ "$completed" = "1" ]; then
    echo "✅ Following discovery complete for all seeds."
    exit 0
  fi

  echo "🔄 Daily FOLLOWING run (start_offset=${next_offset}, max_requests=${MAX_FOLLOWING_REQUESTS}, started $(date))"
  set +e
  python3 packages/scraper/src/discover_instagram_following.py \
    --start-seed-offset "$next_offset" \
    --max-following-requests "$MAX_FOLLOWING_REQUESTS" \
    --delay "$DELAY_SECONDS"
  exit_code=$?
  set -e
  if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 2 ]; then
    echo "❌ discover_instagram_following.py failed with exit code $exit_code"
    exit "$exit_code"
  fi

  python3 packages/scraper/src/merge_instagram_graph_sources.py

  python3 - <<'PY'
import json
from pathlib import Path
report = json.loads(Path("packages/scraper/instagram_following_report.json").read_text(encoding="utf-8"))
state = {
    "next_seed_offset": int(report.get("next_seed_offset", 0)),
    "completed": bool(report.get("all_seeds_processed", False)),
    "last_run": {
        "processed_seed_count": int(report.get("processed_seed_count", 0)),
        "following_requests_made": int(report.get("following_requests_made", 0)),
        "run_candidate_count": int(report.get("run_candidate_count", 0)),
    }
}
Path("packages/scraper/instagram_following_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
print(json.dumps(state, indent=2))
PY

  if [ "$exit_code" -eq 2 ]; then
    echo "✅ All seeds processed for following."
    exit 0
  fi

  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((DAY_SECONDS - elapsed))
  if [ "$sleep_sec" -gt 0 ]; then
    echo "⏸ Waiting ${sleep_sec}s (~$((sleep_sec / 3600))h) until next run..."
    sleep "$sleep_sec"
  fi
done
