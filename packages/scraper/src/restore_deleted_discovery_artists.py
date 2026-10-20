#!/usr/bin/env python3
"""
Re-score artists removed by revert_discovery_created_batch.py and restore JSONs
that pass tattoo_confidence (and optional studio policy).

Metadata sources (in order):
  1. git HEAD:data/artists/<id>.json (if tracked)
  2. packages/scraper/instagram_discovered_candidates_probed.json

Restore:
  - Artists with score >= threshold: git checkout HEAD -- data/artists/<id>.json
  - Studios (classify_account_type == studio): restored but stamped verified=studio

Does not re-upload R2 images; run enrich_instagram_rapidapi.py for missing assets.

  python3 packages/scraper/src/restore_deleted_discovery_artists.py
  python3 packages/scraper/src/restore_deleted_discovery_artists.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from _repo_root import repo_path
from tattoo_scoring import classify_account_type, tattoo_confidence


def _git(*args: str) -> bytes:
    root = str(repo_path())
    return subprocess.check_output(["git", "-C", root, *args])


def write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def git_show_json(rel_path: str) -> dict | None:
    try:
        raw = _git("show", f"HEAD:{rel_path}")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError):
        return None


def load_ids_txt(path: Path) -> list[str]:
    if path.exists():
        ids = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if ids:
            return ids
    raw = _git("show", "HEAD:packages/scraper/instagram_discovery_created_ids.txt")
    return [ln.strip() for ln in raw.decode().splitlines() if ln.strip()]


def load_probe_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {k: v for k, v in loaded.items() if isinstance(k, str) and isinstance(v, dict)}


def git_tracked_artist_ids() -> set[str]:
    out: set[str] = set()
    for line in _git("ls-files", "data/artists").decode().splitlines():
        if line.endswith(".json"):
            out.add(line.rsplit("/", 1)[-1][:-5])
    return out


def _int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def metadata_for_score(handle: str, git_data: dict | None, probe: dict | None) -> dict:
    discovery = (git_data or {}).get("discovery") if isinstance((git_data or {}).get("discovery"), dict) else {}
    ig = (git_data or {}).get("instagram_enriched") if isinstance((git_data or {}).get("instagram_enriched"), dict) else {}
    probe = probe or {}

    full_name = (
        probe.get("full_name")
        if probe.get("probe_status") == "ok"
        else None
    ) or (git_data or {}).get("name")
    biography = probe.get("biography") if probe.get("probe_status") == "ok" else (git_data or {}).get("bio")
    if biography is None and isinstance(git_data, dict):
        biography = git_data.get("bio")

    return {
        "full_name": full_name if isinstance(full_name, str) else None,
        "biography": biography if isinstance(biography, str) else None,
        "evidence_count": _int(discovery.get("evidence_count")) or 0,
        "follower_count": _int(probe.get("follower_count")) or _int(ig.get("follower_count")),
        "media_count": _int(probe.get("media_count")) or _int(ig.get("media_count")),
        "is_private": probe.get("is_private") if isinstance(probe.get("is_private"), bool) else ig.get("is_private"),
        "is_verified": probe.get("is_verified") if isinstance(probe.get("is_verified"), bool) else ig.get("is_verified"),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Restore deleted discovery artists that pass tattoo_confidence.")
    p.add_argument(
        "--ids-file",
        type=str,
        default="packages/scraper/instagram_discovery_created_ids.txt",
        help="Batch ids (one per line). Falls back to git HEAD created_ids if empty/missing.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Minimum tattoo_confidence to restore (same as auto-create gate).",
    )
    p.add_argument("--min-followers", type=int, default=3000)
    p.add_argument(
        "--include-existing",
        action="store_true",
        help="Score even if JSON already exists on disk (default: only missing).",
    )
    p.add_argument(
        "--restore-studios",
        action="store_true",
        default=True,
        help="Restore studios but stamp verified=studio (default: true).",
    )
    p.add_argument(
        "--skip-studios",
        action="store_true",
        help="Do not restore accounts classified as studio.",
    )
    p.add_argument("--apply", action="store_true")
    p.add_argument(
        "--report",
        type=str,
        default="packages/scraper/instagram_discovery_restore_report.json",
    )
    p.add_argument("--limit", type=int, default=None, help="Optional cap for testing.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    missing_only = not args.include_existing

    ids_path = Path(args.ids_file)
    if not ids_path.is_absolute():
        ids_path = repo_path(*ids_path.parts)
    batch_ids = load_ids_txt(ids_path)
    if not batch_ids:
        raise SystemExit("No batch ids found (ids file empty and git HEAD created_ids missing).")

    artists_dir = repo_path("data", "artists")
    probe_cache_path = repo_path("packages", "scraper", "instagram_discovered_candidates_probed.json")
    probe_cache = load_probe_cache(probe_cache_path)
    tracked = git_tracked_artist_ids()

    today = datetime.now().strftime("%Y-%m-%d")
    to_score: list[str] = []
    for artist_id in batch_ids:
        if missing_only and (artists_dir / f"{artist_id}.json").exists():
            continue
        to_score.append(artist_id)
        if args.limit is not None and len(to_score) >= args.limit:
            break

    passed: list[dict] = []
    failed: list[dict] = []
    skipped_no_metadata = 0

    for artist_id in to_score:
        handle = artist_id.lower()
        rel = f"data/artists/{artist_id}.json"
        git_data = git_show_json(rel) if artist_id in tracked else None
        probe = probe_cache.get(handle) or probe_cache.get(artist_id)

        if git_data is None and probe is None:
            skipped_no_metadata += 1
            continue

        meta = metadata_for_score(handle, git_data, probe)
        score, reasons = tattoo_confidence(
            username=handle,
            full_name=meta["full_name"],
            biography=meta["biography"],
            evidence_count=meta["evidence_count"],
            follower_count=meta["follower_count"],
            media_count=meta["media_count"],
            is_private=meta["is_private"],
            is_verified=meta["is_verified"],
            min_followers=args.min_followers,
        )
        kind, kind_reasons = classify_account_type(
            username=handle,
            full_name=meta["full_name"],
            biography=meta["biography"],
        )

        row = {
            "username": artist_id,
            "score": round(score, 4),
            "score_reasons": reasons,
            "kind": kind,
            "kind_reasons": kind_reasons,
            "has_git_json": git_data is not None,
            "follower_count": meta["follower_count"],
            "evidence_count": meta["evidence_count"],
        }

        if score < args.threshold:
            failed.append(row)
            continue
        if args.skip_studios and kind == "studio":
            failed.append({**row, "rejected_as": "studio"})
            continue
        passed.append(row)

    restored = 0
    studio_stamped = 0
    restore_failed = 0

    if args.apply and passed:
        for row in passed:
            artist_id = row["username"]
            rel = f"data/artists/{artist_id}.json"
            if artist_id not in tracked:
                restore_failed += 1
                continue
            try:
                subprocess.check_call(["git", "-C", str(repo_path()), "checkout", "HEAD", "--", rel])
                restored += 1
            except subprocess.CalledProcessError:
                restore_failed += 1
                continue

            if args.restore_studios and row["kind"] == "studio":
                path = artists_dir / f"{artist_id}.json"
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if data.get("verified") != "studio":
                        data["verified"] = "studio"
                        write_json_atomic(path, data)
                        studio_stamped += 1
                except Exception as exc:
                    print(f"  [warn] could not stamp studio {artist_id}: {exc}", file=sys.stderr)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = repo_path(*report_path.parts)

    summary = {
        "ran_at": today,
        "dry_run": not args.apply,
        "batch_ids_total": len(batch_ids),
        "scored_count": len(to_score),
        "skipped_no_metadata": skipped_no_metadata,
        "threshold": args.threshold,
        "min_followers": args.min_followers,
        "passed_count": len(passed),
        "failed_count": len(failed),
        "restored_count": restored,
        "studio_stamped": studio_stamped,
        "restore_failed_no_git": restore_failed,
        "passed": passed,
        "failed_sample": failed[:200],
    }
    write_json_atomic(report_path, summary)

    print(
        f"Scored {len(to_score)} missing batch artists "
        f"(threshold={args.threshold}): pass={len(passed)} fail={len(failed)} "
        f"no_metadata={skipped_no_metadata}"
    )
    if args.apply:
        print(f"Restored {restored} JSONs from git HEAD ({studio_stamped} stamped studio).")
    else:
        print("Dry-run only. Pass --apply to restore JSON files.")
    print(f"Report: {report_path}")
    if passed[:8]:
        print("Sample PASS:")
        for r in passed[:8]:
            print(
                f"  @{r['username']:<28} score={r['score']:<5} kind={r['kind']:<8} "
                f"followers={r['follower_count']}"
            )


if __name__ == "__main__":
    main()
