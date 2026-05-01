#!/usr/bin/env python3
"""
Retroactively clean up artist JSONs that were auto-created from the Instagram
graph (``discovery.source == "instagram_graph"``).

Two-pass policy:

1. **Junk pass** — any artist whose ``tattoo_confidence`` score is below
   ``--auto-create-threshold`` is treated as junk. Its JSON is quarantined
   (default) or deleted (``--delete``). To preserve API spend, the probe
   cache (``instagram_discovered_candidates_probed.json``) is seeded from the
   existing ``instagram_enriched`` block so the next phase2 cycle re-rejects
   the handle without re-probing or re-enriching.

2. **Studio pass** — among the remaining artists (score >= threshold), those
   that ``classify_account_type`` flags as ``"studio"`` are kept on disk but
   stamped with ``data["verified"] = "studio"``. The website's
   ``isArtistHidden`` filter then hides them from public listings, while
   the admin tooling still has access for review.

Usage:
  # Dry-run (default): print plan, change nothing.
  python3 packages/scraper/src/prune_discovery_artists.py

  # Apply: quarantine junk + stamp studios.
  python3 packages/scraper/src/prune_discovery_artists.py --apply

  # Apply, but delete junk instead of quarantining it.
  python3 packages/scraper/src/prune_discovery_artists.py --apply --delete

  # Custom threshold / quarantine dir.
  python3 packages/scraper/src/prune_discovery_artists.py --apply \\
      --auto-create-threshold 0.4 \\
      --quarantine packages/scraper/quarantine_discovery
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from _repo_root import repo_path
from tattoo_scoring import classify_account_type, tattoo_confidence


DEFAULT_PROBE_CACHE = repo_path("packages", "scraper", "instagram_discovered_candidates_probed.json")
DEFAULT_REPORT = repo_path("packages", "scraper", "instagram_discovery_pruned_report.json")
DEFAULT_QUARANTINE = repo_path("packages", "scraper", "quarantine_discovery")


def write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_probe_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {k: v for k, v in loaded.items() if isinstance(k, str) and isinstance(v, dict)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prune sub-threshold discovery artists and stamp studios.")
    p.add_argument(
        "--auto-create-threshold",
        type=float,
        default=0.40,
        help="Score below which an artist is considered junk and pruned.",
    )
    p.add_argument(
        "--min-followers",
        type=int,
        default=1000,
        help="Follower threshold used inside tattoo_confidence scoring.",
    )
    p.add_argument(
        "--probe-cache",
        type=str,
        default=str(DEFAULT_PROBE_CACHE),
        help="Probe cache to seed with metadata from pruned artists.",
    )
    p.add_argument(
        "--report",
        type=str,
        default=str(DEFAULT_REPORT),
        help="Where to write the prune report (kept artists + pruned artists).",
    )
    p.add_argument(
        "--quarantine",
        type=str,
        default=str(DEFAULT_QUARANTINE),
        help="Directory to move pruned files into. Use --delete to skip quarantine.",
    )
    p.add_argument(
        "--delete",
        action="store_true",
        help="Permanently delete junk JSONs instead of moving them to --quarantine.",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually move/delete files, stamp studios, and update probe cache.",
    )
    p.add_argument(
        "--include-non-discovery",
        action="store_true",
        help="Also score artists without discovery.source == instagram_graph (default: skip).",
    )
    p.add_argument(
        "--no-stamp-studios",
        action="store_true",
        help="Skip the studio-stamping pass (only run the junk pass).",
    )
    return p.parse_args()


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    args = parse_args()
    artists_dir = repo_path("data", "artists")
    if not artists_dir.is_dir():
        print(f"Artists dir not found: {artists_dir}", file=sys.stderr)
        sys.exit(1)

    probe_cache_path = Path(args.probe_cache) if Path(args.probe_cache).is_absolute() else repo_path(args.probe_cache)
    probe_cache = load_probe_cache(probe_cache_path)
    quarantine_dir = Path(args.quarantine).resolve() if args.quarantine else None
    if args.apply and not args.delete and quarantine_dir is not None:
        quarantine_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    pruned: list[dict[str, Any]] = []
    studios: list[dict[str, Any]] = []
    kept_artists: list[dict[str, Any]] = []
    skipped_non_discovery = 0
    seeded_cache_entries = 0
    studio_stamps_applied = 0
    studio_stamps_already = 0

    for path in sorted(artists_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  [skip] {path.name}: unreadable ({exc})", file=sys.stderr)
            continue
        if not isinstance(data, dict):
            continue

        discovery = data.get("discovery") if isinstance(data.get("discovery"), dict) else {}
        if not args.include_non_discovery and discovery.get("source") != "instagram_graph":
            skipped_non_discovery += 1
            continue

        handle = path.stem.lower()
        ig = data.get("instagram_enriched") if isinstance(data.get("instagram_enriched"), dict) else {}
        biography = data.get("bio") if isinstance(data.get("bio"), str) else None
        full_name = data.get("name") if isinstance(data.get("name"), str) else None
        evidence_count = _coerce_int(discovery.get("evidence_count")) or 0
        follower_count = _coerce_int(ig.get("follower_count"))
        media_count = _coerce_int(ig.get("media_count"))
        is_private = ig.get("is_private") if isinstance(ig.get("is_private"), bool) else None
        is_verified = ig.get("is_verified") if isinstance(ig.get("is_verified"), bool) else None

        score, reasons = tattoo_confidence(
            username=handle,
            full_name=full_name,
            biography=biography,
            evidence_count=evidence_count,
            follower_count=follower_count,
            media_count=media_count,
            is_private=is_private,
            is_verified=is_verified,
            min_followers=args.min_followers,
        )

        # --- Junk pass --------------------------------------------------------
        if score < args.auto_create_threshold:
            record = {
                "username": handle,
                "score": round(score, 4),
                "score_reasons": reasons,
                "evidence_count": evidence_count,
                "follower_count": follower_count,
                "is_private": is_private,
                "path": str(path),
            }
            pruned.append(record)

            cache_entry = {
                "probe_status": "ok" if (biography or follower_count is not None or media_count is not None) else "seeded",
                "probed_at": today,
                "biography": biography,
                "follower_count": follower_count,
                "following_count": _coerce_int(ig.get("following_count")),
                "media_count": media_count,
                "is_private": is_private,
                "is_verified": is_verified,
                "full_name": full_name,
                "instagram_id": (str(ig.get("id")).strip() if ig.get("id") is not None else None) or discovery.get("instagram_id"),
                "seeded_from": "prune_discovery_artists",
            }
            existing_cache = probe_cache.get(handle)
            if not (existing_cache and existing_cache.get("probe_status") == "ok"):
                probe_cache[handle] = cache_entry
                seeded_cache_entries += 1

            if args.apply:
                try:
                    if args.delete:
                        path.unlink()
                    else:
                        target = quarantine_dir / path.name
                        shutil.move(str(path), str(target))
                except Exception as exc:
                    print(f"  [error] could not prune {path.name}: {exc}", file=sys.stderr)
            continue

        # --- Studio pass ------------------------------------------------------
        kind, kind_reasons = classify_account_type(
            username=handle, full_name=full_name, biography=biography
        )
        if kind == "studio" and not args.no_stamp_studios:
            studios.append({
                "username": handle,
                "score": round(score, 4),
                "kind": kind,
                "kind_reasons": kind_reasons,
                "evidence_count": evidence_count,
                "follower_count": follower_count,
            })
            if data.get("verified") == "studio":
                studio_stamps_already += 1
            elif args.apply:
                data["verified"] = "studio"
                try:
                    write_json_atomic(path, data)
                    studio_stamps_applied += 1
                except Exception as exc:
                    print(f"  [error] could not stamp studio {path.name}: {exc}", file=sys.stderr)
            continue

        kept_artists.append({
            "username": handle,
            "score": round(score, 4),
            "kind": kind,
            "evidence_count": evidence_count,
            "follower_count": follower_count,
        })

    if args.apply:
        write_json_atomic(probe_cache_path, probe_cache)
        report_path = Path(args.report) if Path(args.report).is_absolute() else repo_path(args.report)
        report = {
            "applied": True,
            "ran_at": today,
            "threshold": args.auto_create_threshold,
            "min_followers": args.min_followers,
            "kept_artist_count": len(kept_artists),
            "pruned_count": len(pruned),
            "studio_count": len(studios),
            "studio_stamps_applied": studio_stamps_applied,
            "studio_stamps_already_present": studio_stamps_already,
            "skipped_non_discovery": skipped_non_discovery,
            "seeded_cache_entries": seeded_cache_entries,
            "quarantine_dir": str(quarantine_dir) if (quarantine_dir and not args.delete) else None,
            "probe_cache": str(probe_cache_path),
            "kept_artists_sample": kept_artists[:50],
            "studios": studios,
            "pruned_sample": pruned[:200],
        }
        write_json_atomic(report_path, report)
        print(
            f"Pruned {len(pruned)} junk artists, "
            f"stamped {studio_stamps_applied} studios (already-stamped: {studio_stamps_already}), "
            f"kept {len(kept_artists)} individual artists. "
            f"Seeded {seeded_cache_entries} probe-cache entries. "
            f"Report: {report_path}"
        )
    else:
        print(
            f"[DRY RUN] would prune {len(pruned)} junk artists, "
            f"stamp {len(studios)} studios as verified=studio, "
            f"keep {len(kept_artists)} individual artists "
            f"(threshold={args.auto_create_threshold}, min_followers={args.min_followers}). "
            f"Re-run with --apply to act."
        )
        print()
        print("Sample JUNK to prune (first 5):")
        for r in pruned[:5]:
            print(
                f"  - @{r['username']:<28} score={r['score']:<5} "
                f"reasons={','.join(r['score_reasons']) or '-'} "
                f"evidence={r['evidence_count']} followers={r['follower_count']}"
            )
        print()
        print("Sample STUDIOS to stamp (first 5):")
        for r in studios[:5]:
            print(
                f"  - @{r['username']:<28} score={r['score']:<5} "
                f"reason={','.join(r['kind_reasons']) or '-'} "
                f"followers={r['follower_count']}"
            )
        print()
        print("Sample KEPT artists (first 5):")
        for r in kept_artists[:5]:
            print(
                f"  - @{r['username']:<28} score={r['score']:<5} "
                f"kind={r['kind']:<8} followers={r['follower_count']}"
            )


if __name__ == "__main__":
    main()
