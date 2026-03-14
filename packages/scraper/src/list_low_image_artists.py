#!/usr/bin/env python3
"""
List artist IDs that have fewer than 5 images (tattoos).
Use for targeted enrichment or other pipelines.

Run from repo root:
  PYTHONPATH=packages/scraper/src python3 packages/scraper/src/list_low_image_artists.py [--output FILE] [--with-instagram-only]
"""

import argparse
import json
import sys
from pathlib import Path

from _repo_root import repo_path


def main():
    ap = argparse.ArgumentParser(description="List artist IDs with fewer than 5 images.")
    ap.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write IDs to this file (default: packages/scraper/low_image_artist_ids.json)",
    )
    ap.add_argument(
        "--with-instagram-only",
        action="store_true",
        help="Only include artists that have an Instagram link (for enrich --only-ids-file).",
    )
    ap.add_argument(
        "--max-images",
        type=int,
        default=4,
        help="Include artists with at most this many images (default: 4, i.e. < 5).",
    )
    args = ap.parse_args()

    compact_path = repo_path("data", "indexes", "artists.compact.json")
    if not compact_path.exists():
        print("Run scripts/build_indexes.py first to create data/indexes/artists.compact.json", file=sys.stderr)
        sys.exit(1)

    with open(compact_path, encoding="utf-8") as f:
        artists = json.load(f)

    max_count = max(0, args.max_images)
    low_ids = []
    low_with_ig = []
    for a in artists:
        aid = a.get("id")
        if not aid:
            continue
        count = a.get("tattoo_count") or 0
        if isinstance(a.get("tattoos"), list):
            count = max(count, len(a["tattoos"]))
        if count > max_count:
            continue
        low_ids.append(aid)
        ig = (a.get("links") or {}).get("instagram") or ""
        if ig and ig.strip():
            low_with_ig.append(aid)

    total = len(artists)
    print(f"Total artists: {total}")
    print(f"With fewer than 5 images (count <= {max_count}): {len(low_ids)}")
    print(f"  of those with Instagram: {len(low_with_ig)}")

    out_path = args.output
    if out_path is None:
        out_path = str(repo_path("packages", "scraper", "low_image_artist_ids.json"))
    ids_to_write = low_with_ig if args.with_instagram_only else low_ids
    if ids_to_write and out_path:
        p = Path(out_path)
        if not p.is_absolute():
            p = repo_path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(ids_to_write, f, indent=2)
        print(f"Wrote {len(ids_to_write)} IDs to {p}")
    elif out_path and not ids_to_write:
        print("No IDs to write.", file=sys.stderr)


if __name__ == "__main__":
    main()
