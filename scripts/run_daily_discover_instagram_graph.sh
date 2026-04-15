#!/bin/bash
# Daily unattended Instagram graph discovery with resume state.
# Processes seeds in batches under API limits until all artists are covered.
#
# Run once in screen:
#   bash scripts/run_daily_discover_instagram_graph.sh

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

if [ -z "${RAPIDAPI_KEY:-}" ]; then
  echo "RAPIDAPI_KEY is not set. Export it before running."
  exit 1
fi

DAY_SECONDS=$((24 * 3600))
STATE_FILE="packages/scraper/instagram_discovery_state.json"
RUN_REPORT="packages/scraper/instagram_discovery_report.json"
RUN_RAW="packages/scraper/instagram_discovery_graph_raw.json"
ALL_RAW="packages/scraper/instagram_discovery_graph_all.json"

# Tunables via env
DELAY_SECONDS="${DELAY_SECONDS:-1.2}"                    # keeps under 1 req/sec
MAX_FOLLOWING_REQUESTS="${MAX_FOLLOWING_REQUESTS:-1400}" # below 1500/day limit
MIN_EVIDENCE="${MIN_EVIDENCE:-2}"
MIN_FOLLOWERS="${MIN_FOLLOWERS:-1000}"
AUTO_CREATE_THRESHOLD="${AUTO_CREATE_THRESHOLD:-0.75}"
CREATE_ARTISTS="${CREATE_ARTISTS:-0}"                    # set CREATE_ARTISTS=1 to enable creation

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
state = json.loads(Path("packages/scraper/instagram_discovery_state.json").read_text(encoding="utf-8"))
print(int(state.get("next_seed_offset", 0)))
PY
)

  completed=$(python3 - <<'PY'
import json
from pathlib import Path
state = json.loads(Path("packages/scraper/instagram_discovery_state.json").read_text(encoding="utf-8"))
print("1" if state.get("completed") else "0")
PY
)

  if [ "$completed" = "1" ]; then
    echo "✅ Instagram graph discovery already completed for all seeds. Exiting."
    exit 0
  fi

  echo "🔄 Daily IG graph run (start_offset=${next_offset}, max_following_requests=${MAX_FOLLOWING_REQUESTS}, started $(date))"

  DISCOVER_ARGS=(
    --start-seed-offset "$next_offset"
    --max-following-requests "$MAX_FOLLOWING_REQUESTS"
    --min-evidence "$MIN_EVIDENCE"
    --min-followers "$MIN_FOLLOWERS"
    --auto-create-threshold "$AUTO_CREATE_THRESHOLD"
    --delay "$DELAY_SECONDS"
  )
  if [ "$CREATE_ARTISTS" = "1" ]; then
    DISCOVER_ARGS+=(--create-artists)
  fi

  set +e
  python3 packages/scraper/src/discover_instagram_graph.py "${DISCOVER_ARGS[@]}"
  exit_code=$?
  set -e

  if [ "$exit_code" -ne 0 ] && [ "$exit_code" -ne 2 ]; then
    echo "❌ discover_instagram_graph.py failed with exit code $exit_code"
    exit "$exit_code"
  fi

  # Merge this run's raw graph into cumulative file (union by username).
  python3 - <<'PY'
import json
from pathlib import Path
run_raw = Path("packages/scraper/instagram_discovery_graph_raw.json")
all_raw = Path("packages/scraper/instagram_discovery_graph_all.json")
if not run_raw.exists():
    raise SystemExit(0)
current = json.loads(run_raw.read_text(encoding="utf-8"))
existing = []
if all_raw.exists():
    existing = json.loads(all_raw.read_text(encoding="utf-8"))
by_username = {}
for row in existing:
    u = row.get("username")
    if isinstance(u, str):
        by_username[u] = row
for row in current:
    u = row.get("username")
    if not isinstance(u, str):
        continue
    prev = by_username.get(u, {})
    fb = set(prev.get("followed_by_known_artists") or []) | set(row.get("followed_by_known_artists") or [])
    sm = set(prev.get("similar_to_known_artists") or []) | set(row.get("similar_to_known_artists") or [])
    merged = {
        "username": u,
        "instagram_id": row.get("instagram_id") or prev.get("instagram_id"),
        "full_name": row.get("full_name") or prev.get("full_name"),
        "followed_by_known_artists": sorted(fb),
        "similar_to_known_artists": sorted(sm),
        "followed_by_count": len(fb),
        "similar_to_count": len(sm),
        "evidence_count": len(fb | sm),
    }
    by_username[u] = merged
all_rows = sorted(by_username.values(), key=lambda x: x.get("username", ""))
all_raw.write_text(json.dumps(all_rows, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Merged cumulative graph rows: {len(all_rows)}")
PY

  # Update state from report
  python3 - <<'PY'
import json
from pathlib import Path
report_path = Path("packages/scraper/instagram_discovery_report.json")
state_path = Path("packages/scraper/instagram_discovery_state.json")
if not report_path.exists():
    raise SystemExit("Report not found after discovery run.")
report = json.loads(report_path.read_text(encoding="utf-8"))
state = {
    "next_seed_offset": int(report.get("next_seed_offset", 0)),
    "completed": bool(report.get("all_seeds_processed", False)),
    "last_run": {
        "processed_seed_count": int(report.get("processed_seed_count", 0)),
        "following_requests_made": int(report.get("following_requests_made", 0)),
        "rate_limited_seed_count": int(report.get("rate_limited_seed_count", 0)),
        "candidate_count": int(report.get("candidate_count", 0)),
        "shortlisted_count": int(report.get("shortlisted_count", 0)),
        "accepted_count": int(report.get("accepted_count", 0)),
        "created_count": int(report.get("created_count", 0)),
    }
}
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
print(json.dumps(state, indent=2))
PY

  if [ "$exit_code" -eq 2 ]; then
    echo "✅ All seeds processed. Exiting."
    exit 0
  fi

  echo "✅ Daily batch done."
  elapsed=$(($(date +%s) - run_start))
  sleep_sec=$((DAY_SECONDS - elapsed))
  if [ "$sleep_sec" -gt 0 ]; then
    echo "⏸ Waiting ${sleep_sec}s (~$((sleep_sec / 3600))h) until next run (24h from batch start)..."
    sleep "$sleep_sec"
  fi
done
