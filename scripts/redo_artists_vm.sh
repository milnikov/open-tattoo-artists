#!/bin/bash
# Re-run update_artist_jsons.py for artists that have strange styles and/or < 30 images.
# Run from repo root on VM: ./scripts/redo_artists_vm.sh
# Uses data/artists_redo_ids.txt (one artist ID per line).

set -e
cd "$(dirname "$0")/.."
source venv/bin/activate

IDS_FILE="data/artists_redo_ids.txt"
if [[ ! -f "$IDS_FILE" ]]; then
  echo "Missing $IDS_FILE."
  exit 1
fi

# Sorted list of artist IDs (same order as update_artist_jsons.py)
SORTED_LIST=$(mktemp)
trap "rm -f $SORTED_LIST" EXIT
for f in data/artists/*.json; do basename "$f" .json; done | sort > "$SORTED_LIST"

count=$(grep -c . "$IDS_FILE" 2>/dev/null || echo 0)
echo "Redoing $count artists (strange styles and/or < 30 images)..."
n=0
while IFS= read -r id || [[ -n "$id" ]]; do
  [[ -z "$id" ]] && continue
  n=$((n + 1))
  line=$(grep -nFx "$id" "$SORTED_LIST" | cut -d: -f1)
  if [[ -z "$line" ]]; then
    echo "[$n/$count] Skip $id (not found)"
    continue
  fi
  idx=$((line - 1))
  echo "[$n/$count] $id (index=$idx)"
  ./venv/bin/python packages/scraper/src/update_artist_jsons.py --start-index "$idx" --limit 1 || true
done < "$IDS_FILE"
echo "Done."
