#!/usr/bin/env python3
"""
Merge artist JSON files that share the same Instagram profile (duplicate Tattoofilter
slugs for the same person). Keeps one file per handle, merges tattoos (deduped by
image URL), renumbers image_id, deletes the extra JSONs.

Run from repo root:
  python scripts/dedupe_artists_by_instagram.py
  python scripts/dedupe_artists_by_instagram.py --dry-run

Then rebuild indexes:
  python scripts/build_indexes.py

Optional: remove duplicate tattoo rows inside each file (same image URL twice):
  python scripts/dedupe_artists_by_instagram.py --intra-file-tattoos
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTISTS_DIR = REPO_ROOT / "data" / "artists"

IG_RE = re.compile(r"instagram\.com/([^/?#]+)", re.I)

BOGUS_IG = frozenset(
    {
        "gmail.com",
        "gmail.",
        "tattoodo",
        "inkedmag",
        "facebook.com",
        "youtube.com",
        "linktr.ee",
        "etsy.com",
        "behance.net",
    }
)


def norm_ig(url: object) -> str | None:
    if not url or not isinstance(url, str):
        return None
    u = url.strip().lower().rstrip("/")
    m = IG_RE.search(u)
    if not m:
        return None
    return m.group(1).strip("/").lstrip("@")


def is_plausible_handle(h: str) -> bool:
    if not h or len(h) < 2:
        return False
    if h in BOGUS_IG:
        return False
    if ".com" in h or ".net" in h or ".org" in h:
        return False
    if h.isdigit():
        return False
    return True


def tattoo_url_key(t: dict) -> str | None:
    u = t.get("image_full") or t.get("image_thumb")
    if not u or not isinstance(u, str):
        return None
    return u.strip().lower().split("?")[0]


def artist_score(data: dict) -> tuple[int, int, int, str]:
    """Return sort key: prefer more tattoos, longer bio, longer name, stable id."""
    tattoos = data.get("tattoos") or []
    bio = data.get("bio") or ""
    name = data.get("name") or ""
    return (len(tattoos), len(bio), len(name), str(data.get("id") or ""))


def pick_keeper(paths: list[Path]) -> Path:
    scored: list[tuple[tuple, Path, dict]] = []
    ig_handle: str | None = None
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        if ig_handle is None:
            ig_handle = norm_ig((data.get("links") or {}).get("instagram"))
        scored.append((artist_score(data), p, data))

    def tie_key(item: tuple[tuple, Path, dict]) -> tuple:
        score, path, data = item
        stem = path.stem
        # Prefer slug matching Instagram handle exactly
        match_ig = 0 if (ig_handle and stem.lower() == ig_handle.lower()) else 1
        return (-score[0], -score[1], -score[2], match_ig, stem)

    scored.sort(key=tie_key)
    return scored[0][1]


def merge_tattoos(keeper_data: dict, others: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []

    def add_from(data: dict) -> None:
        for t in data.get("tattoos") or []:
            if not isinstance(t, dict):
                continue
            k = tattoo_url_key(t)
            if k is None:
                continue
            if k in seen:
                continue
            seen.add(k)
            merged.append(deepcopy(t))

    add_from(keeper_data)
    for o in others:
        add_from(o)

    for i, t in enumerate(merged, start=1):
        t["image_id"] = f"{i:03d}"
    return merged


def merge_meta(keeper: dict, others: list[dict]) -> None:
    kbio = (keeper.get("bio") or "").strip()
    kname = (keeper.get("name") or "").strip()
    klinks = keeper.get("links") or {}

    for o in others:
        obio = (o.get("bio") or "").strip()
        oname = (o.get("name") or "").strip()
        if len(obio) > len(kbio):
            keeper["bio"] = o["bio"]
            kbio = obio
        if not kname and oname:
            keeper["name"] = o["name"]
            kname = oname
        ol = o.get("links") or {}
        for key in ("instagram", "website", "source"):
            if not (klinks.get(key) or "").strip() and (ol.get(key) or "").strip():
                klinks[key] = ol[key]
    keeper["links"] = klinks


def dedupe_intratile_tattoos() -> int:
    """Drop duplicate tattoo entries in each JSON (same image_full / image_thumb URL)."""
    changed = 0
    for p in sorted(ARTISTS_DIR.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        tattoos = data.get("tattoos") or []
        if not tattoos:
            continue
        seen: set[str] = set()
        out: list[dict] = []
        for t in tattoos:
            if not isinstance(t, dict):
                continue
            k = tattoo_url_key(t)
            if not k or k in seen:
                continue
            seen.add(k)
            out.append(t)
        if len(out) >= len(tattoos):
            continue
        for i, t in enumerate(out, start=1):
            t["image_id"] = f"{i:03d}"
        data["tattoos"] = out
        data["updated_at"] = date.today().isoformat()
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed += 1
    return changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print plan only")
    ap.add_argument(
        "--intra-file-tattoos",
        action="store_true",
        help="Only dedupe tattoo rows within each JSON (same image URL), then exit",
    )
    args = ap.parse_args()

    if args.intra_file_tattoos:
        n = dedupe_intratile_tattoos()
        print(f"Rewrote {n} artist JSON files (intra-file tattoo dedupe).")
        return

    by_ig: defaultdict[str, list[Path]] = defaultdict(list)
    for p in sorted(ARTISTS_DIR.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        ig = norm_ig((data.get("links") or {}).get("instagram"))
        if ig and is_plausible_handle(ig):
            by_ig[ig].append(p)

    dup_groups = {k: v for k, v in by_ig.items() if len(v) > 1}
    total_remove = sum(len(v) - 1 for v in dup_groups.values())

    print(f"Duplicate groups (same Instagram handle): {len(dup_groups)}")
    print(f"JSON files to remove after merge: {total_remove}")

    if args.dry_run:
        for ig in sorted(dup_groups.keys())[:30]:
            paths = dup_groups[ig]
            k = pick_keeper(paths)
            drop = [p for p in paths if p != k]
            print(f"  {ig}: keep {k.name}, drop {[p.name for p in drop]}")
        if len(dup_groups) > 30:
            print(f"  ... and {len(dup_groups) - 30} more groups")
        return

    removed = 0
    merged_groups = 0
    for ig, paths in sorted(dup_groups.items(), key=lambda x: x[0]):
        keeper_path = pick_keeper(paths)
        others_paths = [p for p in paths if p != keeper_path]
        keeper = json.loads(keeper_path.read_text(encoding="utf-8"))
        others_data = [json.loads(p.read_text(encoding="utf-8")) for p in others_paths]

        keeper["tattoos"] = merge_tattoos(keeper, others_data)
        merge_meta(keeper, others_data)
        keeper["updated_at"] = date.today().isoformat()

        keeper_path.write_text(json.dumps(keeper, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        merged_groups += 1

        for p in others_paths:
            p.unlink()
            removed += 1

    print(f"Merged {merged_groups} groups; removed {removed} duplicate JSON files.")


if __name__ == "__main__":
    main()
