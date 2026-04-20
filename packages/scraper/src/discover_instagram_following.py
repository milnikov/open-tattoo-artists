#!/usr/bin/env python3
"""
Collect raw Instagram "following" graph only.

Purpose:
- maximize usage of following API quota (1500/day) independently,
- persist resume offset so daily runs continue where previous stopped,
- store cumulative raw graph evidence for downstream merge/scoring.
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

BASE_URL = "https://instagram-best-experience.p.rapidapi.com"
FOLLOWING_ENDPOINT = "following"
PROFILE_ENDPOINT = "https://instagram-scraper-stable-api.p.rapidapi.com/ig_get_fb_profile_v3.php"

RUN_RAW_PATH = repo_path("packages", "scraper", "instagram_following_raw.json")
ALL_RAW_PATH = repo_path("packages", "scraper", "instagram_following_all.json")
REPORT_PATH = repo_path("packages", "scraper", "instagram_following_report.json")


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


def headers(api_key: str, host: str, content_type: str | None = None) -> dict[str, str]:
    h = {"x-rapidapi-key": api_key, "x-rapidapi-host": host}
    if content_type:
        h["Content-Type"] = content_type
    return h


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


def load_seeds() -> list[dict[str, str | None]]:
    artists_dir = repo_path("data", "artists")
    seeds: list[dict[str, str | None]] = []
    for p in sorted(artists_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        username = sanitize_handle((data.get("links") or {}).get("instagram"))
        if not username:
            continue
        ig_id = (data.get("instagram_enriched") or {}).get("id")
        seeds.append({"username": username, "instagram_id": str(ig_id).strip() if ig_id else None})
    return seeds


def resolve_seed_user_id(
    api_key: str,
    username: str,
    *,
    delay: float,
    max_attempts: int,
) -> str | None:
    try:
        resp = request_with_backoff(
            "POST",
            PROFILE_ENDPOINT,
            data={"username_or_url": username},
            headers=headers(
                api_key,
                "instagram-scraper-stable-api.p.rapidapi.com",
                content_type="application/x-www-form-urlencoded",
            ),
            max_attempts=max_attempts,
            base_delay=delay,
        )
        payload = resp.json()
    except Exception:
        return None
    user = payload.get("user_data") if isinstance(payload, dict) and isinstance(payload.get("user_data"), dict) else payload
    if not isinstance(user, dict):
        return None
    raw = user.get("id") or user.get("pk")
    return str(raw).strip() if raw is not None and str(raw).strip() else None


def fetch_following(
    api_key: str,
    user_id: str,
    *,
    delay: float,
    max_attempts: int,
    request_budget: int | None,
) -> tuple[list[dict[str, Any]], int, bool]:
    rows: list[dict[str, Any]] = []
    req_count = 0
    next_max_id: str | None = None
    seen: set[str] = set()
    budget_stop = False
    while True:
        if request_budget is not None and req_count >= request_budget:
            budget_stop = True
            break
        params: dict[str, str] = {"user_id": user_id}
        if next_max_id:
            params["next_max_id"] = next_max_id
        try:
            resp = request_with_backoff(
                "GET",
                f"{BASE_URL}/{FOLLOWING_ENDPOINT}",
                params=params,
                headers=headers(api_key, "instagram-best-experience.p.rapidapi.com"),
                max_attempts=max_attempts,
                base_delay=delay,
            )
            req_count += 1
            payload = resp.json()
        except Exception as exc:
            print(f"[following] user_id={user_id} failed: {exc}", file=sys.stderr)
            break
        users = payload.get("users") if isinstance(payload, dict) else []
        if not isinstance(users, list) or not users:
            break
        rows.extend([x for x in users if isinstance(x, dict)])
        cursor = (
            payload.get("next_max_id")
            or payload.get("next_cursor")
            or (payload.get("pagination") or {}).get("next_max_id")
        ) if isinstance(payload, dict) else None
        if not cursor:
            break
        next_max_id = str(cursor)
        if next_max_id in seen:
            break
        seen.add(next_max_id)
        time.sleep(max(0.0, delay))
    return rows, req_count, budget_stop


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
        fb = set(prev.get("followed_by_known_artists") or []) | set(row.get("followed_by_known_artists") or [])
        by_username[u] = {
            "username": u,
            "instagram_id": row.get("instagram_id") or prev.get("instagram_id"),
            "full_name": row.get("full_name") or prev.get("full_name"),
            "followed_by_known_artists": sorted(fb),
            "followed_by_count": len(fb),
        }
    return sorted(by_username.values(), key=lambda x: x.get("username", ""))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect following graph only.")
    p.add_argument("--seed-username", type=str, default=None)
    p.add_argument("--start-seed-offset", type=int, default=0)
    p.add_argument("--limit-seeds", type=int, default=None)
    p.add_argument("--max-following-requests", type=int, default=1400)
    p.add_argument("--delay", type=float, default=1.2)
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
        seeds = [s for s in seeds if s.get("username") == target]
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
    req_used_total = 0
    processed = 0
    budget_stop = False
    candidates: dict[str, dict[str, Any]] = {}

    for i, seed in enumerate(seeds, start=1):
        if req_used_total >= args.max_following_requests:
            budget_stop = True
            break
        username = seed.get("username") or ""
        seed_id = seed.get("instagram_id")
        if not username:
            continue
        processed += 1
        print(f"[{i}/{len(seeds)}] seed @{username}")
        if not seed_id:
            seed_id = resolve_seed_user_id(api_key, username, delay=args.delay, max_attempts=args.max_attempts)
        if not seed_id:
            continue
        remaining = max(0, args.max_following_requests - req_used_total)
        users, req_used, stopped = fetch_following(
            api_key,
            seed_id,
            delay=args.delay,
            max_attempts=args.max_attempts,
            request_budget=remaining,
        )
        req_used_total += req_used
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
                    "followed_by_known_artists": set(),
                },
            )
            row["followed_by_known_artists"].add(username)
        if stopped:
            budget_stop = True
            break

    run_rows: list[dict[str, Any]] = []
    for row in candidates.values():
        fb = sorted(row["followed_by_known_artists"])
        run_rows.append(
            {
                "username": row["username"],
                "instagram_id": row.get("instagram_id"),
                "full_name": row.get("full_name"),
                "followed_by_known_artists": fb,
                "followed_by_count": len(fb),
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
        "mode": "following",
        "total_seed_count": total_seed_count,
        "start_seed_offset": start_offset,
        "processed_seed_count": processed,
        "next_seed_offset": next_offset,
        "all_seeds_processed": all_processed,
        "following_requests_made": req_used_total,
        "max_following_requests": args.max_following_requests,
        "stopped_due_to_following_cap": budget_stop,
        "run_candidate_count": len(run_rows),
        "cumulative_candidate_count": len(all_rows),
        "run_raw_path": str(RUN_RAW_PATH),
        "all_raw_path": str(ALL_RAW_PATH),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"Done. processed_seeds={processed} next_offset={next_offset} "
        f"run_candidates={len(run_rows)} cumulative_candidates={len(all_rows)} "
        f"following_requests={req_used_total}"
    )
    if all_processed:
        sys.exit(2)


if __name__ == "__main__":
    main()
