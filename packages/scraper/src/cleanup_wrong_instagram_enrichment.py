#!/usr/bin/env python3
"""
Remove wrong-handle Instagram enrichment from artist JSONs.

For each artist id in --only-ids-file (JSON array):
  - Drop `instagram_enriched` entirely
  - Remove `tattoos[]` entries whose `image_id` starts with `ig_`

Optional:
  - --delete-r2: delete R2 objects for that artist:
      artists/<id>/instagram/*
      artists/<id>/full/ig_*.webp
      artists/<id>/thumb/ig_*.webp

Uses packages/scraper/config.yaml for R2 (same as enrich). Run from repo root:

  python3 packages/scraper/src/cleanup_wrong_instagram_enrichment.py --dry-run
  python3 packages/scraper/src/cleanup_wrong_instagram_enrichment.py
  python3 packages/scraper/src/cleanup_wrong_instagram_enrichment.py --delete-r2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _repo_root import repo_path


def load_config():
    import yaml

    config_path = repo_path("packages", "scraper", "config.yaml")
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"Expected JSON array in {path}")
    return [str(x).strip() for x in data if x]


def is_ig_tattoo(t: dict) -> bool:
    iid = str((t or {}).get("image_id") or "")
    return iid.startswith("ig_")


def delete_r2_ig_assets(client, bucket: str, artist_id: str, dry_run: bool) -> int:
    """Delete instagram/ prefix and ig_*.webp in full/ and thumb/. Returns delete count."""
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")

    def delete_prefix(prefix: str) -> None:
        nonlocal deleted
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                if dry_run:
                    print(f"  [r2 dry-run] would delete {key}", file=sys.stderr)
                else:
                    client.delete_object(Bucket=bucket, Key=key)
                deleted += 1

    delete_prefix(f"artists/{artist_id}/instagram/")

    for kind in ("full", "thumb"):
        prefix = f"artists/{artist_id}/{kind}/"
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                name = key.rsplit("/", 1)[-1]
                if name.startswith("ig_") and name.endswith(".webp"):
                    if dry_run:
                        print(f"  [r2 dry-run] would delete {key}", file=sys.stderr)
                    else:
                        client.delete_object(Bucket=bucket, Key=key)
                    deleted += 1
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Strip wrong IG enrichment from artist JSONs.")
    parser.add_argument(
        "--only-ids-file",
        type=str,
        default="packages/scraper/instagram_link_fix_needs_cleanup_ids.json",
        help="JSON array of artist ids",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions only; do not write or delete R2.")
    parser.add_argument(
        "--delete-r2",
        action="store_true",
        help="Delete R2 objects under artists/<id>/instagram/ and ig_*.webp in full/thumb.",
    )
    args = parser.parse_args()

    ids_path = Path(args.only_ids_file)
    if not ids_path.is_absolute():
        ids_path = repo_path(*ids_path.parts)
    if not ids_path.exists():
        print(f"IDs file not found: {ids_path}", file=sys.stderr)
        sys.exit(1)

    ids = load_ids(ids_path)
    data_dir = repo_path("data", "artists")

    r2_client = None
    r2_bucket = None
    if args.delete_r2:
        config = load_config()
        r2_cfg = (config or {}).get("r2") or {}
        if not r2_cfg.get("access_key_id"):
            print("R2 not configured in packages/scraper/config.yaml (r2.access_key_id).", file=sys.stderr)
            sys.exit(1)
        from r2 import get_r2_client

        r2_client = get_r2_client(
            r2_cfg["account_id"],
            r2_cfg["access_key_id"],
            r2_cfg["secret_access_key"],
        )
        r2_bucket = r2_cfg.get("bucket", "open-tattoo-artists")

    stats = {
        "processed": 0,
        "missing": 0,
        "json_changed": 0,
        "removed_ie": 0,
        "removed_ig_tats": 0,
        "r2_deleted": 0,
    }

    for artist_id in ids:
        stats["processed"] += 1
        p = data_dir / f"{artist_id}.json"
        if not p.exists():
            stats["missing"] += 1
            continue

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Skip {artist_id}: invalid JSON: {e}", file=sys.stderr)
            continue

        had_ie = bool(data.get("instagram_enriched"))
        tattoos = data.get("tattoos") or []
        if not isinstance(tattoos, list):
            tattoos = []
        ig_count = sum(1 for t in tattoos if isinstance(t, dict) and is_ig_tattoo(t))
        new_tats = [t for t in tattoos if isinstance(t, dict) and not is_ig_tattoo(t)]

        changed = False
        if had_ie:
            if args.dry_run:
                print(f"{artist_id}: would remove instagram_enriched", file=sys.stderr)
            else:
                del data["instagram_enriched"]
            changed = True
            stats["removed_ie"] += 1

        if ig_count:
            if args.dry_run:
                print(f"{artist_id}: would remove {ig_count} ig_* tattoo rows", file=sys.stderr)
            else:
                data["tattoos"] = new_tats
            changed = True
            stats["removed_ig_tats"] += ig_count

        if changed and not args.dry_run:
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            stats["json_changed"] += 1

        if args.delete_r2 and r2_client and r2_bucket and (had_ie or ig_count):
            n = delete_r2_ig_assets(r2_client, r2_bucket, artist_id, dry_run=args.dry_run)
            stats["r2_deleted"] += n

    print(json.dumps(stats, indent=2))
    if args.dry_run:
        print("(dry-run: no JSON or R2 changes written)", file=sys.stderr)


if __name__ == "__main__":
    main()
