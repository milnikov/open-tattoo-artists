#!/usr/bin/env python3
"""
Collect raw Instagram "similar accounts" graph only.

Uses a separate daily/monthly budget from following API and keeps independent resume state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests

from _repo_root import repo_path

BASE_URL = "https://instagram-scraper-stable-api.p.rapidapi.com"
SIMILAR_ENDPOINT = "get_ig_similar_accounts.php"

RUN_RAW_PATH = repo_path("packages", "scraper", "instagram_similar_raw.json")
ALL_RAW_PATH = repo_path("packages", "scraper", "instagram_similar_all.json")
REPORT_PATH = repo_path("packages", "scraper", "instagram_similar_report.json")


def load_config() -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    path = repo_path("packages", "scraper", "config.yaml")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def sanitize_handle(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    if not v:
        return None
    if v.startswith("http://") or v.startswith("https://"):
        m = re.match(r"^https?://(?:www\.)?instagram\.com/([^/?#]+)/?$", v, flags=re.I)
        if not m:
            return None
        v = m.group(1).lower()
    if not re.fullmatch(r"[a-z0-9._]{1,30}", v):
        return None
    return v


def request_with_backoff(
    method: str,
    url: str,
    *,
    max_attempts: int,
    base_delay: float,
    **kwargs: Any,
) -> requests.Response:
    delay = max(0.5, base_delay)
    for attempt in range(1, max_attempts + 1):
        try:
            resp = requests.request(method, url, timeout=30, **kwargs)
            if resp.status_code == 429:
                if attempt == max_attempts:
                    resp.raise_for_status()
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
                continue
            resp.raise_for_status()
            return resp
        except Exception:
            if attempt == max_attempts:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise RuntimeError("request failed")


def load_seeds() -> list[str]:
    artists_dir = repo_path("data", "artists")
    out: list[str] = []
    for p in sorted(artists_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        username = sanitize_handle((data.get("links") or {}).get("instagram"))
        if username:
            out.append(username)
    return out


def fetch_similar(
    api_key: str,
    username: str,
    *,
    max_attempts: int,
    delay: float,
) -> list[dict[str, Any]]:
    try:
        resp = request_with_backoff(
            "GET",
            f"{BASE_URL}/{SIMILAR_ENDPOINT}",
            params={"username_or_url": username},
            headers={
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": "instagram-scraper-stable-api.p.rapidapi.com",
            },
            max_attempts=max_attempts,
            base_delay=delay,
        )
        payload = resp.json()
    except Exception as exc:
        print(f"[similar] @{username} failed: {exc}", file=sys.stderr)
        return []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("users"), list):
        return [x for x in payload["users"] if isinstance(x, dict)]
    return []


def merge_cumulative(current_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = []
    if ALL_RAW_PATH.exists():
        existing = json.loads(ALL_RAW_PATH.read_text(encoding="utf-8"))
    by_username: dict[str, dict[str, Any]] = {}
    for row in existing:
        u = row.get("username")
        if isinstance(u, str):
            by_username[u] = row
    for row in current_rows:
        u = row.get("username")
        if not isinstance(u, str):
            continue
        prev = by_username.get(u, {})
        sm = set(prev.get("similar_to_known_artists") or []) | set(row.get("similar_to_known_artists") or [])
        by_username[u] = {
            "username": u,
            "instagram_id": row.get("instagram_id") or prev.get("instagram_id"),
            "full_name": row.get("full_name") or prev.get("full_name"),
            "similar_to_known_artists": sorted(sm),
            "similar_to_count": len(sm),
        }
    return sorted(by_username.values(), key=lambda x: x.get("username", ""))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect similar graph only.")
    p.add_argument("--seed-username", type=str, default=None)
    p.add_argument("--start-seed-offset", type=int, default=0)
    p.add_argument("--limit-seeds", type=int, default=None)
    p.add_argument("--max-similar-requests", type=int, default=1600)
    p.add_argument("--delay", type=float, default=0.2)
    p.add_argument("--max-attempts", type=int, default=4)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config()
    api_key = os.environ.get("RAPIDAPI_KEY") or cfg.get("rapidapi_key")
    if not api_key:
        print("Missing RAPIDAPI_KEY", file=sys.stderr)
        sys.exit(1)

    all_seeds = load_seeds()
    total_seed_count = len(all_seeds)
    seeds = list(all_seeds)
    if args.seed_username:
        target = sanitize_handle(args.seed_username)
        if not target:
            print("Invalid --seed-username", file=sys.stderr)
            sys.exit(1)
        seeds = [s for s in seeds if s == target]
        if not seeds:
            print(f"Seed @{target} not found", file=sys.stderr)
            sys.exit(1)
        start_offset = 0
    else:
        start_offset = max(0, args.start_seed_offset)
        if start_offset > 0:
            seeds = seeds[start_offset:]
        if args.limit_seeds is not None:
            seeds = seeds[: max(0, args.limit_seeds)]
    if not seeds:
        print("No seeds found")
        return

    print(f"Loaded {len(seeds)} seeds (total={total_seed_count}, start_offset={start_offset}).")
    req_used = 0
    processed = 0
    budget_stop = False
    candidates: dict[str, dict[str, Any]] = {}

    for i, seed_username in enumerate(seeds, start=1):
        if req_used >= args.max_similar_requests:
            budget_stop = True
            break
        processed += 1
        print(f"[{i}/{len(seeds)}] seed @{seed_username}")
        users = fetch_similar(api_key, seed_username, max_attempts=args.max_attempts, delay=args.delay)
        req_used += 1
        for user in users:
            handle = sanitize_handle(user.get("username"))
            if not handle:
                continue
            row = candidates.setdefault(
                handle,
                {
                    "username": handle,
                    "instagram_id": str(user.get("pk") or user.get("id") or user.get("pk_id") or "") or None,
                    "full_name": user.get("full_name"),
                    "similar_to_known_artists": set(),
                },
            )
            row["similar_to_known_artists"].add(seed_username)
        time.sleep(max(0.0, args.delay))

    run_rows: list[dict[str, Any]] = []
    for row in candidates.values():
        sm = sorted(row["similar_to_known_artists"])
        run_rows.append(
            {
                "username": row["username"],
                "instagram_id": row.get("instagram_id"),
                "full_name": row.get("full_name"),
                "similar_to_known_artists": sm,
                "similar_to_count": len(sm),
            }
        )
    run_rows.sort(key=lambda x: x.get("username", ""))
    RUN_RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_RAW_PATH.write_text(json.dumps(run_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    all_rows = merge_cumulative(run_rows)
    ALL_RAW_PATH.write_text(json.dumps(all_rows, indent=2, ensure_ascii=False), encoding="utf-8")

    next_offset = min(total_seed_count, start_offset + processed)
    all_processed = next_offset >= total_seed_count
    report = {
        "mode": "similar",
        "total_seed_count": total_seed_count,
        "start_seed_offset": start_offset,
        "processed_seed_count": processed,
        "next_seed_offset": next_offset,
        "all_seeds_processed": all_processed,
        "similar_requests_made": req_used,
        "max_similar_requests": args.max_similar_requests,
        "stopped_due_to_similar_cap": budget_stop,
        "run_candidate_count": len(run_rows),
        "cumulative_candidate_count": len(all_rows),
        "run_raw_path": str(RUN_RAW_PATH),
        "all_raw_path": str(ALL_RAW_PATH),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Done. processed_seeds={processed} next_offset={next_offset} "
        f"run_candidates={len(run_rows)} cumulative_candidates={len(all_rows)} "
        f"similar_requests={req_used}"
    )
    if all_processed:
        sys.exit(2)


if __name__ == "__main__":
    main()
