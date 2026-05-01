#!/usr/bin/env python3
"""
Probe each Instagram graph discovery candidate with the lightweight profile
endpoint to fetch bio + follower stats. Caches results so subsequent cycles
don't re-probe the same handle (each probe costs 1 stable-API call).

Reads:
  packages/scraper/instagram_discovered_candidates.json  (output of merge step)

Writes:
  packages/scraper/instagram_discovered_candidates_probed.json  (cache)

Cache shape:
  {
    "<username>": {
      "probe_status": "ok" | "failed",
      "probed_at": "YYYY-MM-DD",
      "biography": str | null,
      "follower_count": int | null,
      "following_count": int | null,
      "media_count": int | null,
      "is_private": bool | null,
      "is_verified": bool | null,
      "full_name": str | null,
      "instagram_id": str | null
    },
    ...
  }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from _repo_root import repo_path
from stable_api_budget import BudgetExhaustedError, StableApiBudget


HOST = "instagram-scraper-stable-api.p.rapidapi.com"
PROFILE_URL = f"https://{HOST}/ig_get_fb_profile_v3.php"

DEFAULT_INPUT = repo_path("packages", "scraper", "instagram_discovered_candidates.json")
DEFAULT_CACHE = repo_path("packages", "scraper", "instagram_discovered_candidates_probed.json")


def write_json_atomic(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_api_key() -> str | None:
    api_key = os.environ.get("RAPIDAPI_KEY")
    if api_key:
        return api_key
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    cfg_path = repo_path("packages", "scraper", "config.yaml")
    if not cfg_path.exists():
        return None
    try:
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(cfg, dict):
        return cfg.get("rapidapi_key")
    return None


def _request_with_retry(
    url: str,
    *,
    consume_budget,
    headers: dict[str, str],
    data: dict[str, str],
    max_attempts: int = 4,
    base_delay: float = 0.8,
    timeout: int = 30,
) -> requests.Response | None:
    delay = max(0.5, float(base_delay))
    for attempt in range(1, max_attempts + 1):
        if not consume_budget():
            raise BudgetExhaustedError("shared stable-api budget exhausted")
        try:
            resp = requests.post(url, data=data, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            if attempt == max_attempts:
                print(f"  [probe] {url}: {exc}", file=sys.stderr)
                return None
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
            continue
        if resp.status_code == 429:
            if attempt == max_attempts:
                print(f"  [probe] {url}: 429 after {attempt} attempts", file=sys.stderr)
                return None
            ra = resp.headers.get("Retry-After")
            try:
                sleep_for = float(ra) if ra else delay
            except (TypeError, ValueError):
                sleep_for = delay
            time.sleep(max(0.5, sleep_for))
            delay = min(delay * 2, 30.0)
            continue
        if 500 <= resp.status_code < 600:
            if attempt == max_attempts:
                print(
                    f"  [probe] {url}: {resp.status_code} after {attempt} attempts",
                    file=sys.stderr,
                )
                return None
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
            continue
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            print(f"  [probe] {url}: {exc}", file=sys.stderr)
            return None
        return resp
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_profile(payload: Any) -> dict[str, Any]:
    """Pull bio + stats out of the profile_v3 response (shape varies)."""
    if not isinstance(payload, dict):
        return {}
    user = payload.get("user_data") if isinstance(payload.get("user_data"), dict) else payload
    if not isinstance(user, dict):
        user = {}
    edge_followed = user.get("edge_followed_by") if isinstance(user.get("edge_followed_by"), dict) else None
    edge_following = user.get("edge_follow") if isinstance(user.get("edge_follow"), dict) else None
    edge_media = (
        user.get("edge_owner_to_timeline_media")
        if isinstance(user.get("edge_owner_to_timeline_media"), dict)
        else None
    )

    biography = user.get("biography")
    if not isinstance(biography, str) or not biography.strip():
        biography = payload.get("biography") if isinstance(payload.get("biography"), str) else None
    biography = biography.strip() if isinstance(biography, str) and biography.strip() else None

    follower_count = _coerce_int(
        user.get("follower_count")
        or (edge_followed.get("count") if edge_followed else None)
    )
    following_count = _coerce_int(
        user.get("following_count")
        or (edge_following.get("count") if edge_following else None)
    )
    media_count = _coerce_int(
        user.get("media_count")
        or (edge_media.get("count") if edge_media else None)
    )

    raw_id = user.get("id") or user.get("pk") or user.get("pk_id")
    instagram_id = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else None

    return {
        "biography": biography,
        "follower_count": follower_count,
        "following_count": following_count,
        "media_count": media_count,
        "is_private": user.get("is_private") if isinstance(user.get("is_private"), bool) else None,
        "is_verified": user.get("is_verified") if isinstance(user.get("is_verified"), bool) else None,
        "full_name": user.get("full_name") if isinstance(user.get("full_name"), str) else None,
        "instagram_id": instagram_id,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Probe discovery candidates for bio + stats.")
    p.add_argument("--input", type=str, default=str(DEFAULT_INPUT))
    p.add_argument("--cache", type=str, default=str(DEFAULT_CACHE))
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max candidates to probe in this run (caps API spend).",
    )
    p.add_argument(
        "--reprobe-failed",
        action="store_true",
        help="Retry candidates whose previous probe failed.",
    )
    p.add_argument("--max-attempts", type=int, default=4)
    p.add_argument("--base-delay", type=float, default=0.8)
    p.add_argument(
        "--persist-every",
        type=int,
        default=25,
        help="Flush the cache file to disk after every N probes.",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    api_key = _load_api_key()
    if not api_key:
        print(
            "Missing RAPIDAPI_KEY (env or packages/scraper/config.yaml).",
            file=sys.stderr,
        )
        sys.exit(1)

    candidates_path = Path(args.input) if Path(args.input).is_absolute() else repo_path(args.input)
    cache_path = Path(args.cache) if Path(args.cache).is_absolute() else repo_path(args.cache)

    if not candidates_path.exists():
        print(f"Candidates file not found: {candidates_path}", file=sys.stderr)
        return

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    if not isinstance(candidates, list):
        print("Candidates JSON must be a list.", file=sys.stderr)
        sys.exit(1)

    cache: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        try:
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cache = {
                    k: v
                    for k, v in loaded.items()
                    if isinstance(k, str) and isinstance(v, dict)
                }
        except Exception as exc:
            print(
                f"[probe] cache unreadable ({exc}); starting fresh.",
                file=sys.stderr,
            )

    headers = {"x-rapidapi-key": api_key, "x-rapidapi-host": HOST}
    budget = StableApiBudget.from_env()
    today = datetime.now().strftime("%Y-%m-%d")

    probed = 0
    failed = 0
    skipped_cached = 0
    skipped_missing_handle = 0
    budget_stop = False

    for row in candidates:
        if not isinstance(row, dict):
            continue
        username = row.get("username")
        if not isinstance(username, str) or not username:
            skipped_missing_handle += 1
            continue
        cached = cache.get(username)
        if cached:
            status = cached.get("probe_status")
            if status == "ok" or (status == "failed" and not args.reprobe_failed):
                skipped_cached += 1
                continue
        if args.limit is not None and probed >= args.limit:
            print(
                f"[probe] reached --limit {args.limit}; stopping.",
                file=sys.stderr,
            )
            break

        print(f"[probe] @{username}", file=sys.stderr)
        try:
            resp = _request_with_retry(
                PROFILE_URL,
                consume_budget=budget.try_consume,
                headers=headers,
                data={"username_or_url": username},
                max_attempts=args.max_attempts,
                base_delay=args.base_delay,
            )
        except BudgetExhaustedError:
            print("[probe] shared stable-api budget exhausted", file=sys.stderr)
            budget_stop = True
            break

        if resp is None:
            cache[username] = {"probe_status": "failed", "probed_at": today}
            failed += 1
        else:
            try:
                payload = resp.json()
            except ValueError as exc:
                print(f"  [probe] @{username}: bad json ({exc})", file=sys.stderr)
                cache[username] = {"probe_status": "failed", "probed_at": today}
                failed += 1
                continue
            cache[username] = {
                "probe_status": "ok",
                "probed_at": today,
                **extract_profile(payload),
            }
            probed += 1

        if args.persist_every and (probed + failed) % args.persist_every == 0:
            write_json_atomic(cache_path, cache)

    write_json_atomic(cache_path, cache)
    print(
        f"Probed: {probed} new ok, {failed} failed, "
        f"{skipped_cached} skipped (cached), "
        f"{skipped_missing_handle} skipped (missing handle). "
        f"budget_exhausted={budget_stop}. cache={cache_path}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
