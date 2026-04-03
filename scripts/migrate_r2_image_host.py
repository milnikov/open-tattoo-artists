#!/usr/bin/env python3
"""
Rewrite R2 public (r2.dev) image URLs in data/artists/*.json to a custom domain.

Paths stay the same: only the origin changes, e.g.
  https://pub-xxxx.r2.dev/artists/foo/thumb/001.webp
  -> https://img.thetattoo.world/artists/foo/thumb/001.webp

Run from repo root:
  python scripts/migrate_r2_image_host.py --dry-run
  python scripts/migrate_r2_image_host.py
Then:
  python scripts/build_indexes.py

See docs/SETUP_AND_DEPLOY.md (NEXT_PUBLIC_IMAGES_BASE_URL / r2.public_url).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTISTS_DIR = REPO_ROOT / "data" / "artists"


def normalize_base(url: str) -> str:
    u = url.strip().rstrip("/")
    return u


def rewrite_strings(obj, old_prefix: str, new_prefix: str) -> tuple[object, int]:
    """Return (new_obj, replacement_count)."""
    if isinstance(obj, dict):
        total = 0
        new_d: dict = {}
        for k, v in obj.items():
            nv, c = rewrite_strings(v, old_prefix, new_prefix)
            new_d[k] = nv
            total += c
        return new_d, total

    if isinstance(obj, list):
        total = 0
        out = []
        for v in obj:
            nv, c = rewrite_strings(v, old_prefix, new_prefix)
            out.append(nv)
            total += c
        return out, total

    if isinstance(obj, str):
        if obj.startswith(old_prefix):
            return new_prefix + obj[len(old_prefix) :], 1
        return obj, 0

    return obj, 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--old-base",
        default="https://pub-4fe1c204aa1d4ce08395d234befdc73f.r2.dev",
        help="Public R2 host origin to replace (no trailing slash)",
    )
    parser.add_argument(
        "--new-base",
        default="https://img.thetattoo.world",
        help="New image host origin (no trailing slash)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes only, do not write files",
    )
    args = parser.parse_args()

    old_p = normalize_base(args.old_base)
    new_p = normalize_base(args.new_base)

    if not ARTISTS_DIR.is_dir():
        raise SystemExit(f"Missing {ARTISTS_DIR}")

    files_changed = 0
    urls_rewritten = 0
    for path in sorted(ARTISTS_DIR.glob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except (json.JSONDecodeError, OSError) as e:
            print(f"skip {path.name}: {e}")
            continue

        new_data, count = rewrite_strings(data, old_p, new_p)
        if count == 0:
            continue

        urls_rewritten += count
        files_changed += 1

        if not args.dry_run:
            out = json.dumps(
                new_data, indent=2, ensure_ascii=False
            )
            path.write_text(out + "\n", encoding="utf-8")

    mode = "dry-run: would update" if args.dry_run else "updated"
    print(
        f"{mode} {files_changed} files, {urls_rewritten} URL(s) "
        f"({old_p} -> {new_p})"
    )
    if args.dry_run and (files_changed or urls_rewritten):
        print("Re-run without --dry-run to write. Then: python scripts/build_indexes.py")


if __name__ == "__main__":
    main()
