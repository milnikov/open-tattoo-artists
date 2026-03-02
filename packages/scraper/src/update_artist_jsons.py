#!/usr/bin/env python3
"""
Update existing data/artists/*.json with fresh metadata from the source site.
Re-parses each artist page for styles, bio, tattooing_since (and optionally
name, location, website). Does NOT download or upload images.

Run from repo root (use the venv that has scraper deps installed):
  ./venv/bin/python packages/scraper/src/update_artist_jsons.py [--limit N] [--dry-run]
  # or after: source venv/bin/activate
  python packages/scraper/src/update_artist_jsons.py
"""

import argparse
import json
import random
import sys
import time
from datetime import date
from pathlib import Path

# Ensure scraper deps are importable before adding src to path
try:
    import bs4  # noqa: F401
except ModuleNotFoundError:
    print("Missing dependency: bs4 (beautifulsoup4). Install scraper deps:")
    print("  pip install -r packages/scraper/requirements.txt")
    print("Or run with your venv's Python: ./venv/bin/python packages/scraper/src/update_artist_jsons.py ...")
    sys.exit(1)

from _repo_root import repo_path

# Allow importing parse from same package
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import parse_artist_page


def main():
    parser = argparse.ArgumentParser(
        description="Update existing artist JSONs with metadata from source (no images)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of artists to process (default: all)",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Skip this many artists from the start (default: 0)",
    )
    parser.add_argument(
        "--skip-last",
        type=int,
        default=0,
        metavar="N",
        help="Skip last N artists (e.g. 100 to exclude recently scraped)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print changes but do not write JSON",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser headless (default: True)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Show browser window",
    )
    args = parser.parse_args()

    artists_dir = repo_path("data", "artists")
    if not artists_dir.is_dir():
        print(f"❌ Artists dir not found: {artists_dir}")
        sys.exit(1)

    json_files = sorted(artists_dir.glob("*.json"))
    total = len(json_files)
    json_files = json_files[args.start_index :]
    if args.skip_last:
        json_files = json_files[: -args.skip_last]
    if args.limit is not None:
        json_files = json_files[: args.limit]

    parts = [f"start={args.start_index}"]
    if args.skip_last:
        parts.append(f"skip_last={args.skip_last}")
    parts.append(f"limit={args.limit or 'all'}")
    print(f"📂 Found {total} artist JSONs; processing {len(json_files)} ({', '.join(parts)})")
    if args.dry_run:
        print("🔍 Dry run: no files will be written")

    updated = 0
    skipped = 0
    failed = 0

    for i, path in enumerate(json_files):
        artist_id = path.stem
        print(f"\n[{i + 1}/{len(json_files)}] {artist_id}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ⚠️ Failed to read JSON: {e}")
            failed += 1
            continue

        source_url = (data.get("links") or {}).get("source")
        if not source_url or "tattooswizard" not in source_url.lower():
            print(f"  ⏭️ Skip (no tattooswizard source): {source_url or 'missing'}")
            skipped += 1
            continue

        try:
            parsed = parse_artist_page(
                source_url,
                headless=args.headless,
                max_images=0,
                metadata_only=True,
            )
        except Exception as e:
            print(f"  ❌ Parse error: {e}")
            failed += 1
            continue

        if parsed is None:
            print("  ⏭️ Parse returned None (e.g. no Instagram)")
            skipped += 1
            continue

        # Apply updates (only metadata; do not touch tattoos or image URLs)
        changes = []
        if parsed.styles != data.get("styles"):
            data["styles"] = parsed.styles
            changes.append("styles")
        if (parsed.bio or "") != (data.get("bio") or ""):
            data["bio"] = parsed.bio  # can be None to clear
            changes.append("bio")
        if (parsed.tattooing_since or "") != (data.get("tattooing_since") or ""):
            data["tattooing_since"] = parsed.tattooing_since  # can be None to clear
            changes.append("tattooing_since")
        if changes:
            data["updated_at"] = date.today().isoformat()

        if not changes:
            print("  ✓ No changes")
            continue

        print(f"  📝 Updating: {', '.join(changes)}")
        if "styles" in changes:
            print(f"     styles: {parsed.styles}")
        if "bio" in changes and parsed.bio:
            print(f"     bio: {parsed.bio[:80]}...")
        if "tattooing_since" in changes and parsed.tattooing_since:
            print(f"     tattooing_since: {parsed.tattooing_since}")

        if not args.dry_run:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                updated += 1
                print("  ✅ Written")
            except Exception as e:
                print(f"  ❌ Write error: {e}")
                failed += 1
        else:
            updated += 1

        # Rate limit
        if i < len(json_files) - 1:
            delay = random.uniform(3, 6)
            time.sleep(delay)

    print(f"\n📊 Done. Updated: {updated}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
