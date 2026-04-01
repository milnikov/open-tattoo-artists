#!/usr/bin/env python3
"""
Orchestrate: load URLs from discovered_pages.json -> parse -> download -> WEBP -> R2 -> writer -> state.
Run from repo root: python packages/scraper/src/pipeline_main.py

Usage:
  python packages/scraper/src/pipeline_main.py [--start-index N] [--limit M] [--batch-size B] [--no-r2]
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import fcntl
except ImportError:
    fcntl = None  # Windows: no file lock, git may fail when multiple workers push

from _repo_root import repo_path

# Import after path setup
from parse import parse_artist_page
from images import download_and_process_images
from r2 import get_r2_client, upload_artist_images
from writer import build_artist_json, write_artist
from state import load_state, save_state, is_completed, mark_completed, merge_worker_states

# Exit code when all artists in the list have been processed (for run_daily_parallel.sh to stop).
EXIT_ALL_DONE = 2


def artist_id_from_url(url: str) -> str:
    """Best-effort extraction of artist id/handle from source URL."""
    path = urlparse(url).path.rstrip("/")
    if "/artists/" in path:
        return path.split("/artists/")[-1]
    return path.split("/")[-1]


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


def _run_parallel(config: dict, urls: list, limit: int | None, args) -> None:
    """Spawn N workers with disjoint index ranges, wait, then merge state."""
    n = args.workers
    batch_size = args.batch_size or config.get("batch_size") or 100

    # Load main state to get start
    main_state_path = repo_path("packages", "scraper", "scrape_state.json")
    state = load_state(main_state_path)
    last = state["last_index"]
    start = max(last + 1, args.start_index) if last >= 0 else args.start_index
    if start >= len(urls):
        print("   All artists processed. Exiting (run_daily_parallel.sh will stop).")
        sys.exit(EXIT_ALL_DONE)

    total = limit if limit is not None else (len(urls) - start)
    total = min(total, len(urls) - start)
    if total <= 0:
        print("   Nothing to process.")
        return

    chunk_size = (total + n - 1) // n
    ranges = []
    for i in range(n):
        lo = start + i * chunk_size
        hi = min(lo + chunk_size, len(urls))
        if lo < hi:
            ranges.append((lo, hi - lo))

    if not ranges:
        print("   No ranges to assign.")
        return

    script_dir = repo_path("packages", "scraper", "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(script_dir) + (os.pathsep + env.get("PYTHONPATH", "")) if env.get("PYTHONPATH") else str(script_dir)

    cmd_base = [
        sys.executable,
        str(repo_path("packages", "scraper", "src", "pipeline_main.py")),
        "--batch-size", str(batch_size),
    ]
    if args.no_r2:
        cmd_base.append("--no-r2")
    if args.no_git:
        cmd_base.append("--no-git")

    procs = []
    for i, (lo, cnt) in enumerate(ranges):
        cmd = cmd_base + ["--start-index", str(lo), "--limit", str(cnt), "--state-suffix", f"_w{i}"]
        p = subprocess.Popen(cmd, cwd=str(repo_path()), env=env)
        procs.append((i, p))
        print(f"   Worker {i}: indices {lo}-{lo + cnt - 1} (PID {p.pid})")

    for i, p in procs:
        p.wait()
        if p.returncode != 0:
            print(f"   Worker {i} exited with code {p.returncode}")

    suffixes = [f"_w{i}" for i in range(len(ranges))]
    merge_worker_states(suffixes, main_state_path)
    print("   State merged into scrape_state.json")


def _git_lock_path() -> Path:
    return repo_path(".git-push.lock")


def _acquire_git_lock(timeout_sec: float = 300) -> object | None:
    """Acquire exclusive lock for git ops (so parallel workers don't push over each other). Returns open file or None."""
    if fcntl is None:
        return None
    lock_path = _git_lock_path()
    lock_path.touch()
    f = open(lock_path, "w")
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except (OSError, BlockingIOError):
            if time.monotonic() - start > timeout_sec:
                f.close()
                print("⚠️ Git lock timeout; skipping push.")
                return None
            time.sleep(2)


def _release_git_lock(lock_file: object | None) -> None:
    if lock_file is None:
        return
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
    except Exception:
        pass


def git_commit_and_push(branch: str = "main", message: str = "chore: add scraped artists"):
    """Commit data/artists and push. Uses a lock so only one worker pushes at a time; pulls before push."""
    cwd = str(repo_path())
    lock_file = _acquire_git_lock()
    try:
        # Pull so we don't get rejected (non-fast-forward) when another worker already pushed
        subprocess.run(["git", "fetch", "origin", branch], check=True, cwd=cwd, capture_output=True)
        subprocess.run(["git", "merge", "--no-edit", f"origin/{branch}"], cwd=cwd, check=True, capture_output=True)  # no-op if already up to date
        subprocess.run(["git", "add", "data/artists/"], check=True, cwd=cwd)
        status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=cwd)
        if not status.stdout.strip():
            return True  # nothing to commit
        subprocess.run(["git", "commit", "-m", message], check=True, cwd=cwd)
        subprocess.run(["git", "push", "origin", branch], check=True, cwd=cwd)
        print(f"   📤 Pushed: {message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git push failed: {e}")
        return False
    finally:
        _release_git_lock(lock_file)


def main():
    parser = argparse.ArgumentParser(description="Scrape tattooswizard -> R2 + data/artists")
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None, help="Commit every N artists (default: config or 100)")
    parser.add_argument("--no-r2", action="store_true", help="Skip R2 upload (dry run)")
    parser.add_argument("--no-git", action="store_true", help="Do not commit/push")
    parser.add_argument("--state-suffix", type=str, default="", help="State file suffix for parallel workers (e.g. _w0)")
    parser.add_argument("--workers", type=int, default=1, help="Run N workers in parallel (orchestrator mode)")
    args = parser.parse_args()

    config = load_config()
    discovery_file = config.get("discovery_file") or "packages/scraper/discovered_pages.json"
    urls = load_urls(discovery_file)

    # Per-run limit: CLI --limit overrides config max_artists_per_run
    limit = args.limit
    if limit is None and config.get("max_artists_per_run") is not None:
        limit = config["max_artists_per_run"]
        print(f"   Using config max_artists_per_run: {limit} (run once per day on VPS to stay within ~500/day)")

    # Orchestrator mode: spawn N workers, then merge
    if args.workers > 1:
        _run_parallel(config, urls, limit, args)
        return

    # Single-worker mode
    state_path = repo_path("packages", "scraper", f"scrape_state{args.state_suffix}.json") if args.state_suffix else None
    state = load_state(state_path)

    # Batch size: CLI > config > 100
    batch_size = args.batch_size or config.get("batch_size") or 100

    # Resume from last_index+1 or start_index. If all done, exit so run_daily_parallel.sh can stop.
    last = state["last_index"]
    start = max(last + 1, args.start_index) if last >= 0 else args.start_index
    if start >= len(urls):
        print("   All artists processed. Exiting (run_daily_parallel.sh will stop).")
        sys.exit(EXIT_ALL_DONE)
    end = start + limit if limit is not None else len(urls)
    end = min(end, len(urls))
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
    committed = 0

    for i, url in enumerate(urls_to_process):
        idx = start + i
        print(f"\n[{idx+1}/{len(urls)}] {url}")

        # Fast skip by URL slug to avoid opening/parsing already completed artists.
        precheck_id = artist_id_from_url(url)
        if precheck_id and is_completed(precheck_id, state):
            print(f"  ⏭️ Already completed (precheck): {precheck_id}")
            continue

        try:
            parsed = parse_artist_page(url, headless=True, max_images=max_images)
        except Exception as e:
            print(f"  ❌ Parse error: {e}")
            continue

        if parsed is None:
            print("  ⏭️ Skipped (parse failed)")
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
            bio=parsed.bio,
            tattooing_since=parsed.tattooing_since,
        )
        write_artist(handle, data)
        mark_completed(handle, state, idx, state_path)
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

        # Batch commit every batch_size artists
        if not args.no_git and success_count > 0 and success_count % batch_size == 0:
            if git_commit_and_push(message=f"chore: add {batch_size} scraped artists"):
                committed += batch_size

    # Commit any remainder (e.g. with 3 workers each doing ~167, we commit at 100 each; remainder stays uncommitted otherwise)
    if not args.no_git and success_count > committed:
        remainder = success_count - committed
        if git_commit_and_push(message=f"chore: add {remainder} scraped artists"):
            committed += remainder

    print(f"\n📊 Done. Success: {success_count}")
    if committed:
        print(f"   Committed: {committed} artists")


if __name__ == "__main__":
    main()
