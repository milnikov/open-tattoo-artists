#!/usr/bin/env python3
"""
Merge following-only and similar-only cumulative raw files into a unified graph file.
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path

from _repo_root import repo_path

FOLLOWING_ALL = repo_path("packages", "scraper", "instagram_following_all.json")
SIMILAR_ALL = repo_path("packages", "scraper", "instagram_similar_all.json")
MERGED_ALL = repo_path("packages", "scraper", "instagram_discovery_graph_all.json")
LEGACY_RAW = repo_path("packages", "scraper", "instagram_discovery_graph_raw.json")
LEGACY_REPORT = repo_path("packages", "scraper", "instagram_discovery_report.json")
LEGACY_CANDIDATES = repo_path("packages", "scraper", "instagram_discovered_candidates.json")
FOLLOWING_REPORT = repo_path("packages", "scraper", "instagram_following_report.json")
SIMILAR_REPORT = repo_path("packages", "scraper", "instagram_similar_report.json")


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def load_existing_handles() -> set[str]:
    artists_dir = repo_path("data", "artists")
    out: set[str] = set()
    for p in artists_dir.glob("*.json"):
        out.add(p.stem.lower())
    return out


def load_report(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge following/similar raw graph files.")
    p.add_argument(
        "--min-evidence",
        type=int,
        default=2,
        help="Minimum evidence_count for legacy candidates export.",
    )
    p.add_argument(
        "--no-legacy-export",
        action="store_true",
        help="Only write merged graph file (skip legacy workflow files).",
    )
    p.add_argument(
        "--force-empty-overwrite",
        action="store_true",
        help="Allow overwriting legacy discovery files with empty merged data.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    following_rows = load_rows(FOLLOWING_ALL)
    similar_rows = load_rows(SIMILAR_ALL)

    by_username: dict[str, dict] = {}
    for row in following_rows:
        username = row.get("username")
        if not isinstance(username, str):
            continue
        by_username[username] = {
            "username": username,
            "instagram_id": row.get("instagram_id"),
            "full_name": row.get("full_name"),
            "followed_by_known_artists": sorted(set(row.get("followed_by_known_artists") or [])),
            "similar_to_known_artists": [],
        }

    for row in similar_rows:
        username = row.get("username")
        if not isinstance(username, str):
            continue
        current = by_username.setdefault(
            username,
            {
                "username": username,
                "instagram_id": row.get("instagram_id"),
                "full_name": row.get("full_name"),
                "followed_by_known_artists": [],
                "similar_to_known_artists": [],
            },
        )
        if not current.get("instagram_id"):
            current["instagram_id"] = row.get("instagram_id")
        if not current.get("full_name"):
            current["full_name"] = row.get("full_name")
        current["similar_to_known_artists"] = sorted(
            set(current.get("similar_to_known_artists") or [])
            | set(row.get("similar_to_known_artists") or [])
        )

    merged = []
    for username, row in by_username.items():
        fb = sorted(set(row.get("followed_by_known_artists") or []))
        sm = sorted(set(row.get("similar_to_known_artists") or []))
        merged.append(
            {
                "username": username,
                "instagram_id": row.get("instagram_id"),
                "full_name": row.get("full_name"),
                "followed_by_known_artists": fb,
                "similar_to_known_artists": sm,
                "followed_by_count": len(fb),
                "similar_to_count": len(sm),
                "evidence_count": len(set(fb) | set(sm)),
            }
        )
    merged.sort(key=lambda x: x.get("username", ""))
    MERGED_ALL.parent.mkdir(parents=True, exist_ok=True)
    if merged or args.force_empty_overwrite:
        MERGED_ALL.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Merged graph rows: {len(merged)} -> {MERGED_ALL}")
    else:
        print(
            f"Merged graph is empty; keeping existing {MERGED_ALL} "
            "(pass --force-empty-overwrite to replace)."
        )

    if args.no_legacy_export:
        return

    # Backward-compatible exports for existing workflow.
    if not merged and not args.force_empty_overwrite:
        print(
            "Merged graph is empty; keeping legacy discovery files unchanged "
            "(pass --force-empty-overwrite to replace)."
        )
        return

    LEGACY_RAW.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    existing_handles = load_existing_handles()
    candidates = [
        row for row in merged
        if row.get("evidence_count", 0) >= args.min_evidence
        and isinstance(row.get("username"), str)
        and row["username"].lower() not in existing_handles
    ]
    LEGACY_CANDIDATES.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")

    following_report = load_report(FOLLOWING_REPORT)
    similar_report = load_report(SIMILAR_REPORT)
    legacy_report = {
        "mode": "merged_from_split_pipelines",
        "candidate_count": len(merged),
        "shortlisted_count": len(candidates),
        "accepted_count": len(candidates),
        "rejected_count": max(0, len(merged) - len(candidates)),
        "created_count": 0,
        "created_ids": [],
        "min_evidence": args.min_evidence,
        "raw_graph_path": str(LEGACY_RAW),
        "sources": {
            "following_report": str(FOLLOWING_REPORT),
            "similar_report": str(SIMILAR_REPORT),
        },
        "following_summary": {
            "processed_seed_count": following_report.get("processed_seed_count"),
            "next_seed_offset": following_report.get("next_seed_offset"),
            "all_seeds_processed": following_report.get("all_seeds_processed"),
            "following_requests_made": following_report.get("following_requests_made"),
        },
        "similar_summary": {
            "processed_seed_count": similar_report.get("processed_seed_count"),
            "next_seed_offset": similar_report.get("next_seed_offset"),
            "all_seeds_processed": similar_report.get("all_seeds_processed"),
            "similar_requests_made": similar_report.get("similar_requests_made"),
        },
    }
    LEGACY_REPORT.write_text(json.dumps(legacy_report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Updated legacy files: raw={LEGACY_RAW.name}, "
        f"report={LEGACY_REPORT.name}, candidates={LEGACY_CANDIDATES.name}"
    )


if __name__ == "__main__":
    main()
