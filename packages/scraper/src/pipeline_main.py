#!/usr/bin/env python3
"""
Orchestrate: load URLs from discovered_pages.json -> parse -> download -> WEBP -> R2 -> writer -> state.
Run from repo root: python packages/scraper/src/pipeline_main.py

Usage:
  python packages/scraper/src/pipeline_main.py [--start-index N] [--limit M] [--batch-size B] [--no-r2]
"""

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from _repo_root import repo_path

# Import after path setup
from parse import parse_artist_page
from images import download_and_process_images
from r2 import get_r2_client, upload_artist_images
from writer import build_artist_json, write_artist
from state import load_state, save_state, is_completed, mark_completed


def load_config():
    """Load config.yaml from packages/scraper/."""
    import yaml
    config_path = repo_path("packages", "scraper", "config.yaml")
    if not config_path.exists():
        print("❌ packages/scraper/config.yaml not found. Copy from config.example.yaml and fill in.")
        sys.exit(1)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_urls(discovery_file: str) -> list[str]:
    """Load artist URLs from discovery JSON."""
    path = repo_path(discovery_file) if not Path(discovery_file).is_absolute() else Path(discovery_file)
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("artists", [])


def git_commit_and_push(branch: str = "main", message: str = "chore: add scraped artists"):
    """Commit data/artists and push."""
    try:
        subprocess.run(["git", "add", "data/artists/"], check=True, cwd=str(repo_path()))
        subprocess.run(["git", "status", "--short"], check=True, cwd=str(repo_path()))
        subprocess.run(["git", "commit", "-m", message], check=True, cwd=str(repo_path()))
        subprocess.run(["git", "push", "origin", branch], check=True, cwd=str(repo_path()))
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git push failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Scrape tattooswizard -> R2 + data/artists")
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=100, help="Commit every N artists")
    parser.add_argument("--no-r2", action="store_true", help="Skip R2 upload (dry run)")
    parser.add_argument("--no-git", action="store_true", help="Do not commit/push")
    args = parser.parse_args()

    config = load_config()
    discovery_file = config.get("discovery_file") or "packages/scraper/discovered_pages.json"
    urls = load_urls(discovery_file)
    state = load_state()

    # Per-run limit: CLI --limit overrides config max_artists_per_run (for VPS / rate-limit safety)
    limit = args.limit
    if limit is None and config.get("max_artists_per_run") is not None:
        limit = config["max_artists_per_run"]
        print(f"   Using config max_artists_per_run: {limit} (run once per day on VPS to stay within ~500/day)")

    # Resume from last_index or start_index
    start = max(state["last_index"], args.start_index)
    end = start + limit if limit is not None else len(urls)
    urls_to_process = urls[start:end]

    r2_config = config.get("r2") if not args.no_r2 else None
    if not r2_config and not args.no_r2:
        print("❌ R2 config missing in config.yaml. Use --no-r2 for dry run.")
        sys.exit(1)

    client = None
    if r2_config:
        client = get_r2_client(
            r2_config["account_id"],
            r2_config["access_key_id"],
            r2_config["secret_access_key"],
        )
    bucket = r2_config.get("bucket", "open-tattoo-artists") if r2_config else None
    public_url = r2_config.get("public_url") if r2_config else None
    max_images = config.get("max_images_per_artist", 50)
    max_concurrent = config.get("max_concurrent_downloads", 5)
    delay_min = config.get("artist_delay_min_seconds", 3)
    delay_max = config.get("artist_delay_max_seconds", 8)
    delay_every_n = config.get("artist_delay_every_n", 10)
    delay_extra = config.get("artist_delay_extra_seconds", 15)

    print(f"📂 Loaded {len(urls)} artists, processing {start}..{end} ({len(urls_to_process)} URLs)")
    print(f"   Rate limit: {delay_min}-{delay_max}s between artists, +{delay_extra}s every {delay_every_n}")
    if args.no_r2:
        print("⚠️ Running without R2 upload (dry run)")

    success_count = 0
    skip_no_instagram = 0
    committed = 0

    for i, url in enumerate(urls_to_process):
        idx = start + i
        print(f"\n[{idx+1}/{len(urls)}] {url}")

        try:
            parsed = parse_artist_page(url, headless=True, max_images=max_images)
        except Exception as e:
            print(f"  ❌ Parse error: {e}")
            continue

        if parsed is None:
            print("  ⏭️ Skipped (no Instagram)")
            skip_no_instagram += 1
            continue

        handle = parsed.instagram_handle
        if is_completed(handle, state):
            print(f"  ⏭️ Already completed: {handle}")
            continue

        if not parsed.image_urls:
            print("  ⏭️ No images found")
            continue

        # Download and process images
        try:
            pairs = download_and_process_images(
                parsed.image_urls,
                max_concurrent=max_concurrent,
            )
        except Exception as e:
            print(f"  ❌ Download error: {e}")
            continue

        if not pairs:
            print("  ⏭️ No images downloaded")
            continue

        if len(pairs) < len(parsed.image_urls):
            print(f"  ⚠️ Downloaded {len(pairs)}/{len(parsed.image_urls)} (some failed)")

        # Upload to R2
        if client and bucket:
            try:
                tattoos = upload_artist_images(
                    client, bucket, handle, pairs, public_url_base=public_url
                )
            except Exception as e:
                print(f"  ❌ R2 upload error: {e}")
                continue
        else:
            from images import format_image_id
            tattoos = [
                {
                    "image_id": format_image_id(j),
                    "image_full": f"artists/{handle}/full/{format_image_id(j)}.webp",
                    "image_thumb": f"artists/{handle}/thumb/{format_image_id(j)}.webp",
                }
                for j in range(1, len(pairs) + 1)
            ]

        # Write artist JSON
        data = build_artist_json(
            handle=handle,
            name=parsed.name,
            city=parsed.city,
            country=parsed.country,
            styles=parsed.styles,
            instagram_url=parsed.instagram_url,
            website=parsed.website,
            source_url=parsed.source_url,
            tattoos=tattoos,
        )
        write_artist(handle, data)
        mark_completed(handle, state, idx)
        success_count += 1
        print(f"  ✅ {handle} ({len(tattoos)} images)")

        # Rate limit: delay before next artist to avoid being blocked
        if i < len(urls_to_process) - 1:
            delay = random.uniform(delay_min, delay_max)
            print(f"  ⏸ Waiting {delay:.1f}s before next artist...")
            time.sleep(delay)
            if success_count > 0 and success_count % delay_every_n == 0:
                extra = random.uniform(delay_extra * 0.7, delay_extra * 1.3)
                print(f"  ⏸ Extended pause {extra:.1f}s (every {delay_every_n} artists)...")
                time.sleep(extra)

        # Batch commit
        if not args.no_git and success_count > 0 and success_count % args.batch_size == 0:
            if git_commit_and_push(message=f"chore: add {args.batch_size} scraped artists"):
                committed += args.batch_size

    print(f"\n📊 Done. Success: {success_count}, skipped (no Instagram): {skip_no_instagram}")
    if committed:
        print(f"   Committed: {committed} artists")


if __name__ == "__main__":
    main()
