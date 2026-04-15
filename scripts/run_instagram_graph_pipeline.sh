#!/bin/bash
# Discover new artists from Instagram graph, enrich them, then rebuild indexes.
# Run from repo root: bash scripts/run_instagram_graph_pipeline.sh

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

if [ -z "${RAPIDAPI_KEY:-}" ]; then
  echo "RAPIDAPI_KEY is not set. Export it before running."
  exit 1
fi

THRESHOLD="${AUTO_CREATE_THRESHOLD:-0.75}"
MIN_EVIDENCE="${MIN_EVIDENCE:-2}"
MIN_FOLLOWERS="${MIN_FOLLOWERS:-1000}"
SEED_LIMIT="${SEED_LIMIT:-}"

SEED_ARGS=()
if [ -n "$SEED_LIMIT" ]; then
  SEED_ARGS+=(--limit-seeds "$SEED_LIMIT")
fi

echo "1/3 Discovering + auto-creating artists from Instagram graph"
python3 packages/scraper/src/discover_instagram_graph.py \
  --create-artists \
  --min-evidence "$MIN_EVIDENCE" \
  --min-followers "$MIN_FOLLOWERS" \
  --auto-create-threshold "$THRESHOLD" \
  "${SEED_ARGS[@]}"

if [ -f "packages/scraper/instagram_discovery_report.json" ]; then
  CREATED_IDS_FILE="packages/scraper/instagram_discovery_created_ids.txt"
  python3 - <<'PY'
import json
from pathlib import Path
report_path = Path("packages/scraper/instagram_discovery_report.json")
out_path = Path("packages/scraper/instagram_discovery_created_ids.txt")
data = json.loads(report_path.read_text(encoding="utf-8"))
ids = data.get("created_ids") or []
out_path.write_text("\n".join(ids) + ("\n" if ids else ""), encoding="utf-8")
print(f"Wrote {len(ids)} ids to {out_path}")
PY

  if [ -s "$CREATED_IDS_FILE" ]; then
    echo "2/3 Enriching newly created artists from Instagram profile API"
    python3 packages/scraper/src/enrich_instagram_rapidapi.py \
      --only-ids-file "$CREATED_IDS_FILE"
  else
    echo "2/3 No newly created artists to enrich"
  fi
else
  echo "2/3 Discovery report not found; skipping targeted enrich"
fi

echo "3/3 Rebuilding indexes"
python3 scripts/build_indexes.py

echo "Done."
