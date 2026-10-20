#!/usr/bin/env python3
"""
Remove artists created in a discovery create+enrich batch (e.g. un-gated phase2 VM import).

For each id in --ids-file (default: instagram_discovery_created_ids.txt, one handle per line):
  - Delete data/artists/<id>.json if present
  - Delete packages/scraper/quarantine_discovery/<id>.json if present
  - Seed probe cache from the JSON (so create_artists_from_discovery_candidates won't recreate)
  - Optionally delete all R2 objects under artists/<id>/

Also strips those ids from enrich_instagram_state.json and clears the ids file when --apply.

  python3 packages/scraper/src/revert_discovery_created_batch.py --dry-run
  python3 packages/scraper/src/revert_discovery_created_batch.py --apply --delete-r2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from _repo_root import repo_path


def write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_config():
    import yaml

    config_path = repo_path("packages", "scraper", "config.yaml")
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_ids_txt(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"IDs file not found: {path}")
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        h = line.strip()
        if h:
            out.append(h)
    return out


def seed_probe_from_artist(probe_cache: dict, handle: str, data: dict, today: str) -> bool:
    discovery = data.get("discovery") if isinstance(data.get("discovery"), dict) else {}
    ig = data.get("instagram_enriched") if isinstance(data.get("instagram_enriched"), dict) else {}
    biography = data.get("bio") if isinstance(data.get("bio"), str) else None
    full_name = data.get("name") if isinstance(data.get("name"), str) else None

    def _int(v):
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    entry = {
        "probe_status": "ok" if (biography or ig.get("follower_count") is not None) else "seeded",
        "probed_at": today,
        "biography": biography,
        "follower_count": _int(ig.get("follower_count")),
        "following_count": _int(ig.get("following_count")),
        "media_count": _int(ig.get("media_count")),
        "is_private": ig.get("is_private") if isinstance(ig.get("is_private"), bool) else None,
        "is_verified": ig.get("is_verified") if isinstance(ig.get("is_verified"), bool) else None,
        "full_name": full_name,
        "instagram_id": (str(ig.get("id")).strip() if ig.get("id") is not None else None)
        or discovery.get("instagram_id"),
        "seeded_from": "revert_discovery_created_batch",
    }
    existing = probe_cache.get(handle)
    if existing and existing.get("probe_status") == "ok":
        return False
    probe_cache[handle] = entry
    return True


def delete_r2_artist_prefix(client, bucket: str, artist_id: str, dry_run: bool) -> int:
    prefix = f"artists/{artist_id}/"
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        keys = [{"Key": obj["Key"]} for obj in page.get("Contents") or []]
        if not keys:
            continue
        if dry_run:
            deleted += len(keys)
            continue
        for i in range(0, len(keys), 1000):
            batch = keys[i : i + 1000]
            client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
            deleted += len(batch)
    return deleted


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Revert a discovery created-artists batch.")
    p.add_argument(
        "--ids-file",
        type=str,
        default="packages/scraper/instagram_discovery_created_ids.txt",
        help="Text file with one artist handle per line.",
    )
    p.add_argument("--apply", action="store_true", help="Apply deletions (default: dry-run).")
    p.add_argument("--dry-run", action="store_true", help="Print plan only (default if --apply omitted).")
    p.add_argument(
        "--delete-r2",
        action="store_true",
        help="Delete all R2 objects under artists/<id>/ for each id.",
    )
    p.add_argument(
        "--report",
        type=str,
        default="packages/scraper/instagram_discovery_reverted_report.json",
    )
    p.add_argument("--verbose", action="store_true", help="Log each path during dry-run.")
    p.add_argument(
        "--r2-workers",
        type=int,
        default=12,
        help="Parallel R2 prefix deletes (phase 2).",
    )
    p.add_argument(
        "--skip-r2",
        action="store_true",
        help="Only remove JSON/quarantine/state (phase 1).",
    )
    p.add_argument(
        "--r2-only",
        action="store_true",
        help="Only run R2 prefix deletes (phase 2); do not touch local JSON/state.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = args.dry_run or not args.apply

    ids_path = Path(args.ids_file)
    if not ids_path.is_absolute():
        ids_path = repo_path(*ids_path.parts)
    ids = load_ids_txt(ids_path)
    id_set = {h.lower() for h in ids}

    artists_dir = repo_path("data", "artists")
    quarantine_dir = repo_path("packages", "scraper", "quarantine_discovery")
    probe_cache_path = repo_path("packages", "scraper", "instagram_discovered_candidates_probed.json")
    enrich_state_path = repo_path("packages", "scraper", "enrich_instagram_state.json")

    probe_cache: dict = {}
    if probe_cache_path.exists():
        try:
            loaded = json.loads(probe_cache_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                probe_cache = loaded
        except Exception:
            probe_cache = {}

    enrich_state = {"completed_ids": [], "last_index": -1}
    if enrich_state_path.exists():
        try:
            enrich_state = json.loads(enrich_state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    completed = enrich_state.get("completed_ids") or []
    if not isinstance(completed, list):
        completed = []

    r2_client = None
    r2_bucket = None
    do_r2 = args.delete_r2 and not args.skip_r2
    if do_r2:
        config = load_config()
        r2_cfg = (config or {}).get("r2") or {}
        if not r2_cfg.get("access_key_id"):
            print("R2 not configured in packages/scraper/config.yaml", file=sys.stderr)
            sys.exit(1)
        from r2 import get_r2_client

        r2_client = get_r2_client(
            r2_cfg["account_id"],
            r2_cfg["access_key_id"],
            r2_cfg["secret_access_key"],
        )
        r2_bucket = r2_cfg.get("bucket", "open-tattoo-artists")

    today = datetime.now().strftime("%Y-%m-%d")
    stats = {
        "dry_run": dry_run,
        "ids_file": str(ids_path),
        "ids_in_file": len(ids),
        "json_deleted": 0,
        "quarantine_deleted": 0,
        "json_missing": 0,
        "probe_seeded": 0,
        "r2_objects_deleted": 0,
        "enrich_completed_removed": 0,
    }

    # Phase 1: local JSON + quarantine + probe cache seeding
    if not args.r2_only:
        for i, artist_id in enumerate(ids, 1):
            handle = artist_id.lower()
            artist_path = artists_dir / f"{artist_id}.json"
            q_path = quarantine_dir / f"{artist_id}.json"

            if artist_path.exists():
                try:
                    data = json.loads(artist_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    data = {}
                if seed_probe_from_artist(probe_cache, handle, data, today):
                    stats["probe_seeded"] += 1
                if dry_run and args.verbose:
                    print(f"[dry-run] delete JSON {artist_path}", file=sys.stderr)
                elif not dry_run:
                    artist_path.unlink()
                stats["json_deleted"] += 1
            else:
                stats["json_missing"] += 1

            if q_path.exists():
                if dry_run and args.verbose:
                    print(f"[dry-run] delete quarantine {q_path}", file=sys.stderr)
                elif not dry_run:
                    q_path.unlink()
                stats["quarantine_deleted"] += 1

            if not dry_run and i % 2000 == 0:
                print(f"Phase 1: {i}/{len(ids)} ids processed...", file=sys.stderr)

    # Phase 2: R2 (parallel)
    if do_r2 and r2_client and r2_bucket:
        workers = max(1, args.r2_workers)

        def _r2_job(aid: str) -> tuple[str, int]:
            return aid, delete_r2_artist_prefix(r2_client, r2_bucket, aid, dry_run=dry_run)

        if dry_run:
            for artist_id in ids:
                stats["r2_objects_deleted"] += delete_r2_artist_prefix(
                    r2_client, r2_bucket, artist_id, dry_run=True
                )
        else:
            done = 0
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_r2_job, aid): aid for aid in ids}
                for fut in as_completed(futures):
                    _, n = fut.result()
                    stats["r2_objects_deleted"] += n
                    done += 1
                    if done % 500 == 0:
                        print(
                            f"Phase 2 (R2): {done}/{len(ids)} prefixes, "
                            f"{stats['r2_objects_deleted']} objects so far...",
                            file=sys.stderr,
                        )

    removed_from_enrich = [x for x in completed if str(x).lower() in id_set]
    stats["enrich_completed_removed"] = len(removed_from_enrich)
    new_completed = [x for x in completed if str(x).lower() not in id_set]

    if not dry_run and not args.r2_only:
        write_json_atomic(probe_cache_path, probe_cache)
        write_json_atomic(
            enrich_state_path,
            {"completed_ids": sorted(new_completed, key=str), "last_index": enrich_state.get("last_index", -1)},
        )
        ids_path.write_text("", encoding="utf-8")

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = repo_path(*report_path.parts)
    report = {"ran_at": today, **stats}
    if not dry_run:
        write_json_atomic(report_path, report)

    print(json.dumps(stats, indent=2))
    if dry_run:
        print("(dry-run: no changes written; pass --apply to execute)", file=sys.stderr)
    else:
        print(f"Report: {report_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
