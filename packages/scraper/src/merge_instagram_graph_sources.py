#!/usr/bin/env python3
"""
Merge following-only and similar-only cumulative raw files into a unified graph file.
"""

from __future__ import annotations

import json
from pathlib import Path

from _repo_root import repo_path

FOLLOWING_ALL = repo_path("packages", "scraper", "instagram_following_all.json")
SIMILAR_ALL = repo_path("packages", "scraper", "instagram_similar_all.json")
MERGED_ALL = repo_path("packages", "scraper", "instagram_discovery_graph_all.json")


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def main() -> None:
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
    MERGED_ALL.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Merged graph rows: {len(merged)} -> {MERGED_ALL}")


if __name__ == "__main__":
    main()
