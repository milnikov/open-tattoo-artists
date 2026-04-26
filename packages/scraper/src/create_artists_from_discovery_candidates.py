#!/usr/bin/env python3
"""
Create new artist JSON files from discovery candidates.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from _repo_root import repo_path
from writer import build_artist_json, write_artist


def sanitize_handle(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    if not v:
        return None
    if not re.fullmatch(r"[a-z0-9._]{1,30}", v):
        return None
    return v


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create artist JSONs from instagram discovery candidates.")
    p.add_argument(
        "--input",
        type=str,
        default="packages/scraper/instagram_discovered_candidates.json",
        help="Path to candidates JSON list.",
    )
    p.add_argument(
        "--created-ids-output",
        type=str,
        default="packages/scraper/instagram_discovery_created_ids.txt",
        help="Output txt file with created artist IDs (one per line).",
    )
    p.add_argument("--limit", type=int, default=None, help="Optional max artists to create.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = repo_path(args.input)
    output_ids_path = repo_path(args.created_ids_output)
    artists_dir = repo_path("data", "artists")

    if not input_path.exists():
        raise SystemExit(f"Candidates file not found: {input_path}")

    candidates = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(candidates, list):
        raise SystemExit("Candidates JSON must be a list.")

    existing_ids = {p.stem.lower() for p in artists_dir.glob("*.json")}
    created: list[str] = []

    for row in candidates:
        if not isinstance(row, dict):
            continue
        handle = sanitize_handle(row.get("username"))
        if not handle:
            continue
        if handle in existing_ids:
            continue
        raw_full_name = row.get("full_name")
        full_name_clean = raw_full_name.strip() if isinstance(raw_full_name, str) else ""
        name = full_name_clean or handle
        instagram_url = f"https://instagram.com/{handle}"
        raw_bio = row.get("biography")
        bio = raw_bio.strip() if isinstance(raw_bio, str) and raw_bio.strip() else None
        data = build_artist_json(
            handle=handle,
            name=name,
            city="Unknown",
            country="Unknown",
            styles=[],
            instagram_url=instagram_url,
            website=None,
            source_url=instagram_url,
            tattoos=[],
            bio=bio,
        )
        # Keep useful seed metadata for follow-up processing.
        # IMPORTANT: do NOT seed instagram_enriched here — enrich_instagram_rapidapi.py
        # treats any artist with that key as already enriched and skips it forever.
        # The discovery.instagram_id field is read by discover_instagram_following.load_seeds
        # so we still avoid one stable-API resolve_seed_user_id call per new artist.
        discovery: dict = {
            "source": "instagram_graph",
            "followed_by_count": row.get("followed_by_count", 0),
            "similar_to_count": row.get("similar_to_count", 0),
            "evidence_count": row.get("evidence_count", 0),
            "followed_by_known_artists": row.get("followed_by_known_artists", []),
            "similar_to_known_artists": row.get("similar_to_known_artists", []),
        }
        ig_id = row.get("instagram_id")
        if ig_id is not None and str(ig_id).strip() not in ("", "0"):
            discovery["instagram_id"] = str(ig_id).strip()
        data["discovery"] = discovery

        write_artist(handle, data)
        existing_ids.add(handle)
        created.append(handle)
        if args.limit is not None and len(created) >= args.limit:
            break

    output_ids_path.parent.mkdir(parents=True, exist_ok=True)
    output_ids_path.write_text("\n".join(created) + ("\n" if created else ""), encoding="utf-8")
    print(f"Created {len(created)} artists. IDs file: {output_ids_path}")


if __name__ == "__main__":
    main()
