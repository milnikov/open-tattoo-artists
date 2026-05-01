#!/usr/bin/env python3
"""
Create new artist JSON files from Instagram graph discovery candidates,
gated by a tattoo-likelihood score so we don't create JSONs for restaurants,
photographers, gear shops, friends, etc.

Inputs:
  - packages/scraper/instagram_discovered_candidates.json
      (list of candidate rows from merge_instagram_graph_sources.py;
      includes graph evidence + best-effort metadata from discovery rows)
  - packages/scraper/instagram_discovered_candidates_probed.json (optional)
      (cache from probe_discovery_candidates.py; provides bio + follower stats)

Decision:
  Each candidate gets a tattoo_confidence score in [0, 1]. Positive tattoo
  vocabulary must appear in the probed **display name + bio** (mentions
  stripped); graph/followers/media bonuses apply only when that is true.
  We auto-create only if score >= --auto-create-threshold (default 0.75).
  Rejected rows are written to instagram_discovery_rejected.json with their
  score and reasons for transparency.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from _repo_root import repo_path
from tattoo_scoring import tattoo_confidence
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


def write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create artist JSONs from instagram discovery candidates.")
    p.add_argument(
        "--input",
        type=str,
        default="packages/scraper/instagram_discovered_candidates.json",
        help="Path to candidates JSON list.",
    )
    p.add_argument(
        "--probe-cache",
        type=str,
        default="packages/scraper/instagram_discovered_candidates_probed.json",
        help="Path to bio/stats probe cache (output of probe_discovery_candidates.py).",
    )
    p.add_argument(
        "--created-ids-output",
        type=str,
        default="packages/scraper/instagram_discovery_created_ids.txt",
        help="Output txt file with created artist IDs (one per line).",
    )
    p.add_argument(
        "--rejections-output",
        type=str,
        default="packages/scraper/instagram_discovery_rejected.json",
        help="Where to write rejected candidates with score + reasons.",
    )
    p.add_argument(
        "--auto-create-threshold",
        type=float,
        default=0.75,
        help="Minimum tattoo_confidence score to auto-create an artist JSON (0..1).",
    )
    p.add_argument(
        "--min-followers",
        type=int,
        default=3000,
        help="Follower count threshold used inside tattoo_confidence scoring.",
    )
    p.add_argument(
        "--require-probe",
        action="store_true",
        help=(
            "If set, candidates with no probe entry are rejected (reason: no_probe). "
            "Default: score them with whatever metadata is available."
        ),
    )
    p.add_argument("--limit", type=int, default=None, help="Optional max artists to create.")
    return p.parse_args()


def load_probe_cache(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(loaded, dict):
        return {}
    return {
        k: v for k, v in loaded.items() if isinstance(k, str) and isinstance(v, dict)
    }


def main() -> None:
    args = parse_args()
    input_path = repo_path(args.input)
    probe_cache_path = repo_path(args.probe_cache)
    output_ids_path = repo_path(args.created_ids_output)
    rejections_path = repo_path(args.rejections_output)
    artists_dir = repo_path("data", "artists")

    if not input_path.exists():
        raise SystemExit(f"Candidates file not found: {input_path}")

    candidates = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(candidates, list):
        raise SystemExit("Candidates JSON must be a list.")

    probe_cache = load_probe_cache(probe_cache_path)
    existing_ids = {p.stem.lower() for p in artists_dir.glob("*.json")}
    created: list[str] = []
    rejected: list[dict[str, Any]] = []

    today = datetime.now().strftime("%Y-%m-%d")

    for row in candidates:
        if not isinstance(row, dict):
            continue
        handle = sanitize_handle(row.get("username"))
        if not handle:
            continue
        if handle in existing_ids:
            continue

        probe = probe_cache.get(handle) or {}
        probe_ok = probe.get("probe_status") == "ok"

        if args.require_probe and not probe_ok:
            rejected.append(
                {
                    "username": handle,
                    "reason": "no_probe",
                    "score": None,
                    "score_reasons": [],
                    "evidence_count": int(row.get("evidence_count") or 0),
                    "rejected_at": today,
                }
            )
            continue

        full_name = (
            (probe.get("full_name") if probe_ok else None)
            or row.get("full_name")
        )
        biography = probe.get("biography") if probe_ok else None
        follower_count = probe.get("follower_count") if probe_ok else None
        media_count = probe.get("media_count") if probe_ok else None
        is_private = probe.get("is_private") if probe_ok else row.get("is_private")
        is_verified = probe.get("is_verified") if probe_ok else row.get("is_verified")

        evidence_count = int(row.get("evidence_count") or 0)
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

        if score < args.auto_create_threshold:
            rejected.append(
                {
                    "username": handle,
                    "reason": "below_threshold",
                    "score": round(score, 4),
                    "score_reasons": reasons,
                    "threshold": args.auto_create_threshold,
                    "evidence_count": evidence_count,
                    "follower_count": follower_count,
                    "is_private": is_private,
                    "probe_status": probe.get("probe_status"),
                    "rejected_at": today,
                }
            )
            continue

        full_name_clean = full_name.strip() if isinstance(full_name, str) else ""
        name = full_name_clean or handle
        instagram_url = f"https://instagram.com/{handle}"
        bio = biography.strip() if isinstance(biography, str) and biography.strip() else None

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
        # IMPORTANT: do NOT seed instagram_enriched here -- enrich_instagram_rapidapi.py
        # treats any artist with that key as already enriched and skips it forever.
        # The discovery.instagram_id field is read by discover_instagram_following.load_seeds
        # so we still avoid one stable-API resolve_seed_user_id call per new artist.
        discovery: dict[str, Any] = {
            "source": "instagram_graph",
            "followed_by_count": int(row.get("followed_by_count") or 0),
            "similar_to_count": int(row.get("similar_to_count") or 0),
            "evidence_count": evidence_count,
            "followed_by_known_artists": list(row.get("followed_by_known_artists") or []),
            "similar_to_known_artists": list(row.get("similar_to_known_artists") or []),
            "score": round(score, 4),
            "score_reasons": reasons,
            "scored_at": today,
        }
        ig_id = (probe.get("instagram_id") if probe_ok else None) or row.get("instagram_id")
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
    write_json_atomic(rejections_path, rejected)
    print(
        f"Created {len(created)} artists "
        f"(rejected {len(rejected)}, threshold={args.auto_create_threshold}, "
        f"min_followers={args.min_followers}). "
        f"IDs file: {output_ids_path}; rejections: {rejections_path}"
    )


if __name__ == "__main__":
    main()
