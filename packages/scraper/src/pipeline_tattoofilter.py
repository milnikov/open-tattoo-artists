#!/usr/bin/env python3
"""
Pipeline for TattooFilter: load URLs from tattoofilter_new_artists.json,
parse with parse_tattoofilter, download images, R2, write data/artists.
Writes JSON even when 0 images (name, styles, instagram, etc.).
Uses separate state file scrape_state_tattoofilter.json (and _tattoofilter_w0 for workers).

Run from repo root: python packages/scraper/src/pipeline_tattoofilter.py
Or via: scripts/run_daily_parallel_tattoofilter.sh

To create JSONs for artists that were skipped (no images), generate a list of missing handles
and run with --only-handles-file (or --only-urls-file with a list of URLs). State is not updated.

  python3 -c "
  import json, re
  from pathlib import Path
  def slug_to_handle(url): slug = url.rstrip('/').split('/')[-1]; return re.sub(r'[^a-z0-9._-]', '', slug.lower().replace('-', '_'))[:30] or 'unknown'
  urls = json.load(open('packages/scraper/tattoofilter_new_artists.json')).get('artists', [])
  expected = {slug_to_handle(u) for u in urls}
  existing = {p.stem for p in Path('data/artists').glob('*.json')}
  missing = sorted(expected - existing)
  json.dump(missing, open('packages/scraper/tattoofilter_missing_handles.json', 'w'), indent=0)
  print(len(missing), 'missing handles -> packages/scraper/tattoofilter_missing_handles.json')
  "
  python3 packages/scraper/src/pipeline_tattoofilter.py --only-handles-file packages/scraper/tattoofilter_missing_handles.json --no-r2
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

from _repo_root import repo_path

from parse_tattoofilter import parse_artist_page
from images import download_and_process_images
from r2 import get_r2_client, upload_artist_images
from writer import build_artist_json, write_artist
from state import load_state, save_state, is_completed, mark_completed, merge_worker_states

EXIT_ALL_DONE = 2

DISCOVERY_FILE = "packages/scraper/tattoofilter_new_artists.json"
STATE_SUFFIX = "_tattoofilter"


def _url_to_handle(url: str) -> str:
    """Same logic as parse_tattoofilter: slug -> safe handle for filename."""
    import re
    slug = url.rstrip("/").split("/")[-1]
    return re.sub(r"[^a-z0-9._-]", "", slug.lower().replace("-", "_"))[:30] or "unknown"


def _main_state_path() -> Path:
    return repo_path("packages", "scraper", f"scrape_state{STATE_SUFFIX}.json")


def load_config():
    import yaml
    config_path = repo_path("packages", "scraper", "config.yaml")
    if not config_path.exists():
        print("❌ packages/scraper/config.yaml not found. Copy from config.example.yaml and fill in.")
        sys.exit(1)
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_urls(discovery_file: str) -> list:
    path = repo_path(discovery_file) if not Path(discovery_file).is_absolute() else Path(discovery_file)
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("artists", [])


def load_urls_from_file(path: str) -> list:
    """Load URLs from a file: JSON array, JSON {artists: [...]}, or one URL per line."""
    p = Path(path) if Path(path).is_absolute() else repo_path(path)
    if not p.exists():
        return []
    text = p.read_text().strip()
    if not text:
        return []
    # Try JSON first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [u for u in data if isinstance(u, str) and u.strip().startswith("http")]
        if isinstance(data, dict) and "artists" in data:
            return [u for u in data["artists"] if isinstance(u, str) and u.strip().startswith("http")]
    except json.JSONDecodeError:
        pass
    # One URL per line
    return [line.strip() for line in text.splitlines() if line.strip().startswith("http")]


def load_handles_from_file(path: str) -> set:
    """Load handles from a file: JSON array, or one handle per line."""
    p = Path(path) if Path(path).is_absolute() else repo_path(path)
    if not p.exists():
        return set()
    text = p.read_text().strip()
    if not text:
        return set()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return {str(h).strip() for h in data if h}
        return set()
    except json.JSONDecodeError:
        pass
    return {line.strip() for line in text.splitlines() if line.strip()}


def _run_parallel(config: dict, urls: list, limit: int | None, args, only_mode: bool = False) -> None:
    n = args.workers
    batch_size = args.batch_size or config.get("batch_size") or 100
    script_dir = repo_path("packages", "scraper", "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(script_dir) + (os.pathsep + env.get("PYTHONPATH", "")) if env.get("PYTHONPATH") else str(script_dir)

    if only_mode:
        # Write filtered URLs to temp file; workers load it and take their slice via --start-index/--limit
        import tempfile
        fd, only_urls_path = tempfile.mkstemp(suffix=".json", prefix="tattoofilter_only_")
        try:
            os.close(fd)
            with open(only_urls_path, "w") as f:
                json.dump({"artists": urls}, f)
            total = len(urls)
            chunk_size = (total + n - 1) // n
            ranges = []
            for i in range(n):
                lo = i * chunk_size
                hi = min(lo + chunk_size, total)
                if lo < hi:
                    ranges.append((lo, hi - lo))
            if not ranges:
                return
            cmd_base = [
                sys.executable,
                str(repo_path("packages", "scraper", "src", "pipeline_tattoofilter.py")),
                "--only-urls-file", only_urls_path,
                "--batch-size", str(batch_size),
            ]
            if args.no_r2:
                cmd_base.append("--no-r2")
            if args.no_git:
                cmd_base.append("--no-git")
            procs = []
            for i, (lo, cnt) in enumerate(ranges):
                cmd = cmd_base + ["--start-index", str(lo), "--limit", str(cnt)]
                p = subprocess.Popen(cmd, cwd=str(repo_path()), env=env)
                procs.append((i, p))
                print(f"   Worker {i}: indices {lo}-{lo + cnt - 1} ({cnt} URLs) (PID {p.pid})")
            for i, p in procs:
                p.wait()
                if p.returncode != 0:
                    print(f"   Worker {i} exited with code {p.returncode}")
        finally:
            try:
                os.unlink(only_urls_path)
            except Exception:
                pass
        return

    main_state_path = _main_state_path()
    state = load_state(main_state_path)
    last = state["last_index"]
    start = max(last + 1, args.start_index) if last >= 0 else args.start_index
    if start >= len(urls):
        print("   All artists processed. Exiting (run_daily_parallel_tattoofilter.sh will stop).")
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

    cmd_base = [
        sys.executable,
        str(repo_path("packages", "scraper", "src", "pipeline_tattoofilter.py")),
        "--batch-size", str(batch_size),
    ]
    if args.no_r2:
        cmd_base.append("--no-r2")
    if args.no_git:
        cmd_base.append("--no-git")

    procs = []
    for i, (lo, cnt) in enumerate(ranges):
        cmd = cmd_base + ["--start-index", str(lo), "--limit", str(cnt), "--state-suffix", f"{STATE_SUFFIX}_w{i}"]
        p = subprocess.Popen(cmd, cwd=str(repo_path()), env=env)
        procs.append((i, p))
        print(f"   Worker {i}: indices {lo}-{lo + cnt - 1} (PID {p.pid})")

    for i, p in procs:
        p.wait()
        if p.returncode != 0:
            print(f"   Worker {i} exited with code {p.returncode}")

    suffixes = [f"{STATE_SUFFIX}_w{i}" for i in range(len(ranges))]
    merge_worker_states(suffixes, main_state_path)
    print(f"   State merged into {main_state_path.name}")


def _git_lock_path() -> Path:
    return repo_path(".git-push.lock")


def _acquire_git_lock(timeout_sec: float = 300):
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


def _release_git_lock(lock_file):
    if lock_file is None:
        return
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
    except Exception:
        pass


def git_commit_and_push(branch: str = "main", message: str = "chore: add scraped artists (TattooFilter)"):
    cwd = str(repo_path())
    lock_file = _acquire_git_lock()
    try:
        subprocess.run(["git", "fetch", "origin", branch], check=True, cwd=cwd, capture_output=True)
        subprocess.run(["git", "merge", "--no-edit", f"origin/{branch}"], cwd=cwd, check=True, capture_output=True)
        subprocess.run(["git", "add", "data/artists/"], check=True, cwd=cwd)
        status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=cwd)
        if not status.stdout.strip():
            return True
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
    parser = argparse.ArgumentParser(description="Scrape TattooFilter artists -> R2 + data/artists")
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--no-r2", action="store_true", help="Skip R2 upload")
    parser.add_argument("--no-git", action="store_true", help="Do not commit/push")
    parser.add_argument("--state-suffix", type=str, default=STATE_SUFFIX, help=f"State file suffix (default: {STATE_SUFFIX})")
    parser.add_argument("--workers", type=int, default=1, help="Run N workers in parallel")
    parser.add_argument("--only-urls-file", type=str, default=None, help="Process only URLs from this file (JSON array or one per line); write JSON even with 0 images; do not update main state")
    parser.add_argument("--only-handles-file", type=str, default=None, help="Process only artists whose handle is in this file (from discovery list); same as --only-urls-file but filter by handles")
    args = parser.parse_args()

    config = load_config()
    urls = load_urls(DISCOVERY_FILE)
    only_mode = False
    if args.only_urls_file:
        only_urls = load_urls_from_file(args.only_urls_file)
        if only_urls:
            urls = only_urls
            only_mode = True
    elif args.only_handles_file:
        handles = load_handles_from_file(args.only_handles_file)
        if handles:
            urls = [u for u in urls if _url_to_handle(u) in handles]
            only_mode = True

    limit = args.limit
    if limit is None and config.get("max_artists_per_run") is not None and not only_mode:
        limit = config["max_artists_per_run"]
        print(f"   Using config max_artists_per_run: {limit}")

    if args.workers > 1:
        _run_parallel(config, urls, limit, args, only_mode=only_mode)
        return

    state_path = repo_path("packages", "scraper", f"scrape_state{args.state_suffix}.json")
    state = load_state(state_path)

    batch_size = args.batch_size or config.get("batch_size") or 100

    if only_mode:
        # Single run: process all; worker run: parent passed --start-index and --limit for this slice
        if args.start_index > 0 or (args.limit is not None and args.limit < len(urls)):
            start = args.start_index
            end = min(args.start_index + (args.limit or len(urls)), len(urls))
            urls_to_process = urls[start:end]
            print(f"   Only-mode worker: slice {start}..{end} ({len(urls_to_process)} URLs)")
        else:
            start = 0
            end = len(urls)
            urls_to_process = urls
            print(f"   Only-mode: processing {len(urls)} URLs (write JSON even with 0 images, state not updated)")
    else:
        last = state["last_index"]
        start = max(last + 1, args.start_index) if last >= 0 else args.start_index
        if start >= len(urls):
            print("   All artists processed. Exiting.")
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

    print(f"📂 TattooFilter: {len(urls)} artists, processing {start}..{end} ({len(urls_to_process)} URLs)")
    print(f"   State: {state_path.name}")
    if args.no_r2:
        print("⚠️ Running without R2 upload (dry run)")

    success_count = 0
    committed = 0

    for i, url in enumerate(urls_to_process):
        idx = start + i
        print(f"\n[{idx+1}/{len(urls_to_process)}] {url}")

        try:
            parsed = parse_artist_page(url, headless=True, max_images=max_images)
        except Exception as e:
            print(f"  ❌ Parse error: {e}")
            continue

        if parsed is None:
            print("  ⏭️ Skipped (parse failed)")
            continue

        handle = parsed.instagram_handle
        if not only_mode and is_completed(handle, state):
            print(f"  ⏭️ Already completed: {handle}")
            continue

        if not parsed.image_urls:
            # Write JSON with whatever we have (name, styles, instagram, etc.) and empty tattoos
            data = build_artist_json(
                handle=handle,
                name=parsed.name,
                city=parsed.city,
                country=parsed.country,
                styles=parsed.styles,
                instagram_url=parsed.instagram_url,
                website=parsed.website,
                source_url=parsed.source_url,
                tattoos=[],
                bio=parsed.bio,
                tattooing_since=parsed.tattooing_since,
            )
            write_artist(handle, data)
            if not only_mode:
                mark_completed(handle, state, idx, state_path)
            success_count += 1
            print(f"  ✅ {handle} (0 images, metadata only)")
            if i < len(urls_to_process) - 1:
                delay = random.uniform(delay_min, delay_max)
                print(f"  ⏸ Waiting {delay:.1f}s before next artist...")
                time.sleep(delay)
                if success_count > 0 and success_count % delay_every_n == 0:
                    extra = random.uniform(delay_extra * 0.7, delay_extra * 1.3)
                    print(f"  ⏸ Extended pause {extra:.1f}s (every {delay_every_n} artists)...")
                    time.sleep(extra)
            if not args.no_git and success_count > 0 and success_count % batch_size == 0:
                if git_commit_and_push(message=f"chore: add {batch_size} scraped artists (TattooFilter)"):
                    committed += batch_size
            continue

        try:
            pairs = download_and_process_images(parsed.image_urls, max_concurrent=max_concurrent)
        except Exception as e:
            print(f"  ❌ Download error: {e}")
            continue

        if not pairs:
            print("  ⏭️ No images downloaded")
            continue

        if len(pairs) < len(parsed.image_urls):
            print(f"  ⚠️ Downloaded {len(pairs)}/{len(parsed.image_urls)} (some failed)")

        if client and bucket:
            try:
                tattoos = upload_artist_images(client, bucket, handle, pairs, public_url_base=public_url)
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
        if not only_mode:
            mark_completed(handle, state, idx, state_path)
        success_count += 1
        print(f"  ✅ {handle} ({len(tattoos)} images)")

        if i < len(urls_to_process) - 1:
            delay = random.uniform(delay_min, delay_max)
            print(f"  ⏸ Waiting {delay:.1f}s before next artist...")
            time.sleep(delay)
            if success_count > 0 and success_count % delay_every_n == 0:
                extra = random.uniform(delay_extra * 0.7, delay_extra * 1.3)
                print(f"  ⏸ Extended pause {extra:.1f}s (every {delay_every_n} artists)...")
                time.sleep(extra)

        if not args.no_git and success_count > 0 and success_count % batch_size == 0:
            if git_commit_and_push(message=f"chore: add {batch_size} scraped artists (TattooFilter)"):
                committed += batch_size

    if not args.no_git and success_count > committed:
        remainder = success_count - committed
        if git_commit_and_push(message=f"chore: add {remainder} scraped artists (TattooFilter)"):
            committed += remainder

    print(f"\n📊 Done. Success: {success_count}")
    if committed:
        print(f"   Committed: {committed} artists")


if __name__ == "__main__":
    main()
