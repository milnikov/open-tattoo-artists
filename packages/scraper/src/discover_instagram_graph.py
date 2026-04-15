#!/usr/bin/env python3
"""
Discover new tattoo artists from Instagram graph APIs (2-phase).

Phase 1: collect all following/similar candidates (no tattoo filtering).
Phase 2: hydrate basic profile for candidates with enough graph evidence,
         score tattoo likelihood, and optionally create new artist JSON files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from _repo_root import repo_path
from writer import build_artist_json, write_artist

BASE_URL_BEST = "https://instagram-best-experience.p.rapidapi.com"
BASE_URL_STABLE = "https://instagram-scraper-stable-api.p.rapidapi.com"
FOLLOWING_ENDPOINT = "following"
SIMILAR_ENDPOINT = "get_ig_similar_accounts.php"
PROFILE_ENDPOINT = "ig_get_fb_profile_v3.php"

CANDIDATES_PATH = repo_path("packages", "scraper", "instagram_discovered_candidates.json")
REPORT_PATH = repo_path("packages", "scraper", "instagram_discovery_report.json")
RAW_GRAPH_PATH = repo_path("packages", "scraper", "instagram_discovery_graph_raw.json")

POSITIVE_TERMS = {
    "tattoo",
    "tattoos",
    "tattooer",
    "tattooist",
    "tattooartist",
    "ink",
    "inked",
    "fineline",
    "blackwork",
    "dotwork",
    "trad",
    "traditional",
    "irezumi",
    "tattooing",
}
NEGATIVE_TERMS = {
    "meme",
    "news",
    "media",
    "gamer",
    "gaming",
    "restaurant",
    "agency",
    "marketing",
    "crypto",
    "casino",
}


@dataclass
class Candidate:
    username: str
    instagram_id: str | None = None
    full_name: str | None = None
    biography: str | None = None
    is_private: bool | None = None
    is_verified: bool | None = None
    follower_count: int | None = None
    following_count: int | None = None
    media_count: int | None = None
    followed_by_artists: set[str] = field(default_factory=set)
    similar_to_artists: set[str] = field(default_factory=set)
    basic_profile_loaded: bool = False

    def merge_graph_user(self, user: dict[str, Any], seed_username: str, source_kind: str) -> None:
        raw_id = user.get("pk") or user.get("id") or user.get("pk_id")
        if raw_id is not None and str(raw_id).strip():
            self.instagram_id = str(raw_id).strip()
        full_name = user.get("full_name")
        if isinstance(full_name, str) and full_name.strip():
            self.full_name = full_name.strip()
        if isinstance(user.get("is_private"), bool):
            self.is_private = user["is_private"]
        if isinstance(user.get("is_verified"), bool):
            self.is_verified = user["is_verified"]
        if source_kind == "following":
            self.followed_by_artists.add(seed_username)
        if source_kind == "similar":
            self.similar_to_artists.add(seed_username)

    def merge_basic_profile(self, profile_payload: dict[str, Any]) -> None:
        user = profile_payload.get("user_data") if isinstance(profile_payload.get("user_data"), dict) else profile_payload
        if not isinstance(user, dict):
            user = {}
        raw_id = user.get("id") or user.get("pk")
        if raw_id is not None and str(raw_id).strip():
            self.instagram_id = str(raw_id).strip()
        full_name = user.get("full_name")
        if isinstance(full_name, str) and full_name.strip():
            self.full_name = full_name.strip()
        bio = (
            user.get("biography")
            or user.get("bio")
            or profile_payload.get("biography")
            or profile_payload.get("bio")
        )
        if isinstance(bio, str) and bio.strip():
            self.biography = bio.strip()
        if isinstance(user.get("is_private"), bool):
            self.is_private = user["is_private"]
        if isinstance(user.get("is_verified"), bool):
            self.is_verified = user["is_verified"]
        for field in ("follower_count", "following_count", "media_count"):
            raw = user.get(field)
            if isinstance(raw, (int, float)):
                setattr(self, field, int(raw))
            elif isinstance(raw, str) and raw.isdigit():
                setattr(self, field, int(raw))
        self.basic_profile_loaded = True

    def evidence_count(self) -> int:
        return len(self.followed_by_artists | self.similar_to_artists)


def load_config() -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    path = repo_path("packages", "scraper", "config.yaml")
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f)
    return parsed if isinstance(parsed, dict) else {}


def headers_for_host(api_key: str, host: str, *, content_type: str | None = None) -> dict[str, str]:
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host,
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


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


def _request_with_backoff(
    method: str,
    url: str,
    *,
    max_attempts: int,
    base_delay: float,
    **kwargs: Any,
) -> requests.Response:
    delay = max(0.5, base_delay)
    last_exc: Exception | None = None
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
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 30.0)
    raise RuntimeError(f"Request failed: {last_exc}")


def fetch_all_following_by_user_id(
    api_key: str,
    user_id: str,
    *,
    delay_seconds: float,
    max_attempts: int,
    request_budget: int | None = None,
) -> tuple[list[dict[str, Any]], bool, int, bool]:
    users: list[dict[str, Any]] = []
    seen_cursor: set[str] = set()
    next_max_id: str | None = None
    hit_rate_limit = False
    request_count = 0
    stopped_by_budget = False
    while True:
        if request_budget is not None and request_count >= request_budget:
            stopped_by_budget = True
            break
        params = {"user_id": user_id}
        if next_max_id:
            params["next_max_id"] = next_max_id
        try:
            resp = _request_with_backoff(
                "GET",
                f"{BASE_URL_BEST}/{FOLLOWING_ENDPOINT}",
                params=params,
                headers=headers_for_host(api_key, "instagram-best-experience.p.rapidapi.com"),
                max_attempts=max_attempts,
                base_delay=max(0.5, delay_seconds),
            )
            request_count += 1
            payload = resp.json()
        except Exception as exc:
            if "429" in str(exc):
                hit_rate_limit = True
            print(f"[following] user_id={user_id} failed: {exc}", file=sys.stderr)
            break

        page_users = payload.get("users") if isinstance(payload, dict) else []
        if not isinstance(page_users, list) or not page_users:
            break
        users.extend([x for x in page_users if isinstance(x, dict)])

        cursor = (
            payload.get("next_max_id")
            or payload.get("next_cursor")
            or (payload.get("pagination") or {}).get("next_max_id")
        ) if isinstance(payload, dict) else None
        if not cursor:
            break
        next_max_id = str(cursor)
        if next_max_id in seen_cursor:
            break
        seen_cursor.add(next_max_id)
        time.sleep(max(0.0, delay_seconds))
    return users, hit_rate_limit, request_count, stopped_by_budget


def fetch_similar_by_username(api_key: str, username: str, *, max_attempts: int, delay_seconds: float) -> list[dict[str, Any]]:
    try:
        resp = _request_with_backoff(
            "GET",
            f"{BASE_URL_STABLE}/{SIMILAR_ENDPOINT}",
            params={"username_or_url": username},
            headers=headers_for_host(api_key, "instagram-scraper-stable-api.p.rapidapi.com"),
            max_attempts=max_attempts,
            base_delay=max(0.5, delay_seconds),
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


def fetch_basic_profile(api_key: str, username: str, *, max_attempts: int, delay_seconds: float) -> dict[str, Any] | None:
    try:
        resp = _request_with_backoff(
            "POST",
            f"{BASE_URL_STABLE}/{PROFILE_ENDPOINT}",
            data={"username_or_url": username},
            headers=headers_for_host(
                api_key,
                "instagram-scraper-stable-api.p.rapidapi.com",
                content_type="application/x-www-form-urlencoded",
            ),
            max_attempts=max_attempts,
            base_delay=max(0.5, delay_seconds),
        )
        payload = resp.json()
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        print(f"[profile_basic] @{username} failed: {exc}", file=sys.stderr)
        return None


def load_existing_artists() -> tuple[set[str], list[dict[str, str | None]]]:
    artists_dir = repo_path("data", "artists")
    existing: set[str] = set()
    seeds: list[dict[str, str | None]] = []
    for p in sorted(artists_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = sanitize_handle(data.get("id"))
        if aid:
            existing.add(aid)
        links = data.get("links") or {}
        username = sanitize_handle((links or {}).get("instagram"))
        ig_id = (data.get("instagram_enriched") or {}).get("id")
        if username:
            seeds.append({"username": username, "instagram_id": str(ig_id).strip() if ig_id else None})
    return existing, seeds


def tattoo_confidence(c: Candidate, *, min_followers: int) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    text = " ".join([c.username, c.full_name or "", c.biography or ""]).lower()
    pos = sum(1 for t in POSITIVE_TERMS if t in text)
    neg = sum(1 for t in NEGATIVE_TERMS if t in text)
    if pos:
        add = min(0.45, pos * 0.12)
        score += add
        reasons.append(f"tattoo_keywords(+{add:.2f})")
    if neg:
        sub = min(0.4, neg * 0.12)
        score -= sub
        reasons.append(f"non_artist_keywords(-{sub:.2f})")
    ev = c.evidence_count()
    if ev:
        add = min(0.3, ev * 0.06)
        score += add
        reasons.append(f"graph_evidence(+{add:.2f})")
    if c.follower_count is not None and c.follower_count >= min_followers:
        score += 0.15
        reasons.append(f"followers>={min_followers}(+0.15)")
    if c.media_count is not None and c.media_count >= 9:
        score += 0.08
        reasons.append("active_profile(+0.08)")
    if c.is_private is True:
        score -= 0.1
        reasons.append("private_account(-0.10)")
    if c.is_verified:
        score += 0.04
        reasons.append("verified(+0.04)")
    return max(0.0, min(1.0, score)), reasons


def to_artist_json(candidate: Candidate) -> dict[str, Any]:
    username = candidate.username
    instagram_url = f"https://instagram.com/{username}"
    data = build_artist_json(
        handle=username,
        name=(candidate.full_name or username).strip() or username,
        city="Unknown",
        country="Unknown",
        styles=[],
        instagram_url=instagram_url,
        website=None,
        source_url=instagram_url,
        tattoos=[],
        bio=(candidate.biography or "").strip() or None,
    )
    return data


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Discover artists from IG graph in two phases.")
    p.add_argument("--seed-username", type=str, default=None, help="Use only one seed username.")
    p.add_argument("--start-seed-offset", type=int, default=0, help="Start from this seed offset in sorted seed list.")
    p.add_argument("--limit-seeds", type=int, default=None, help="Limit number of seeds.")
    p.add_argument("--delay", type=float, default=1.0, help="Delay between API pages/calls.")
    p.add_argument("--max-attempts", type=int, default=4, help="Max retry attempts for API calls.")
    p.add_argument(
        "--max-following-requests",
        type=int,
        default=None,
        help="Cap daily following endpoint requests in this run (e.g. 1400).",
    )
    p.add_argument("--min-evidence", type=int, default=2, help="Minimum unique seed evidence to hydrate/score.")
    p.add_argument("--min-followers", type=int, default=1000, help="Followers threshold in tattoo scoring.")
    p.add_argument("--auto-create-threshold", type=float, default=0.75, help="Score threshold for auto-create.")
    p.add_argument("--create-artists", action="store_true", help="Create JSON files for accepted candidates.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config()
    api_key = os.environ.get("RAPIDAPI_KEY") or cfg.get("rapidapi_key")
    if not api_key:
        print("Missing RAPIDAPI_KEY.", file=sys.stderr)
        sys.exit(1)

    existing_handles, seeds = load_existing_artists()
    if args.seed_username:
        s = sanitize_handle(args.seed_username)
        if not s:
            print("Invalid --seed-username", file=sys.stderr)
            sys.exit(1)
        seeds = [x for x in seeds if x.get("username") == s]
        if not seeds:
            print(f"Seed @{s} not found in database.", file=sys.stderr)
            sys.exit(1)
    total_seed_count = len(seeds)
    start_seed_offset = max(0, int(args.start_seed_offset or 0))
    if start_seed_offset > 0:
        seeds = seeds[start_seed_offset:]
    if args.limit_seeds is not None:
        seeds = seeds[: max(0, args.limit_seeds)]
    if not seeds:
        print("No seeds found.")
        return

    print(
        f"Loaded {len(seeds)} seeds "
        f"(total={total_seed_count}, start_offset={start_seed_offset})."
    )
    candidates: dict[str, Candidate] = {}
    rate_limited_seeds = 0
    following_requests_made = 0
    processed_seed_count = 0
    stopped_due_to_following_cap = False

    for i, seed in enumerate(seeds, start=1):
        if (
            args.max_following_requests is not None
            and following_requests_made >= args.max_following_requests
        ):
            stopped_due_to_following_cap = True
            break
        seed_username = seed.get("username") or ""
        seed_ig_id = seed.get("instagram_id")
        if not seed_username:
            continue
        processed_seed_count += 1
        print(f"[{i}/{len(seeds)}] seed @{seed_username}")

        if not seed_ig_id:
            seed_profile = fetch_basic_profile(
                api_key,
                seed_username,
                max_attempts=args.max_attempts,
                delay_seconds=args.delay,
            )
            if seed_profile:
                seed_user = (
                    seed_profile.get("user_data")
                    if isinstance(seed_profile.get("user_data"), dict)
                    else seed_profile
                )
                if isinstance(seed_user, dict):
                    raw_seed_id = seed_user.get("id") or seed_user.get("pk")
                    if raw_seed_id is not None and str(raw_seed_id).strip():
                        seed_ig_id = str(raw_seed_id).strip()

        if seed_ig_id:
            remaining_budget = None
            if args.max_following_requests is not None:
                remaining_budget = max(0, args.max_following_requests - following_requests_made)
            following, hit_limit, req_used, budget_stop = fetch_all_following_by_user_id(
                api_key,
                seed_ig_id,
                delay_seconds=args.delay,
                max_attempts=args.max_attempts,
                request_budget=remaining_budget,
            )
            following_requests_made += req_used
            if hit_limit:
                rate_limited_seeds += 1
            for user in following:
                username = sanitize_handle(user.get("username"))
                if not username:
                    continue
                c = candidates.setdefault(username, Candidate(username=username))
                c.merge_graph_user(user, seed_username, "following")
            if budget_stop:
                stopped_due_to_following_cap = True
                break

        similar = fetch_similar_by_username(
            api_key, seed_username, max_attempts=args.max_attempts, delay_seconds=args.delay
        )
        for user in similar:
            username = sanitize_handle(user.get("username"))
            if not username:
                continue
            c = candidates.setdefault(username, Candidate(username=username))
            c.merge_graph_user(user, seed_username, "similar")

    shortlisted: dict[str, Candidate] = {}
    prefiltered_rejected: list[dict[str, Any]] = []
    raw_graph_candidates: list[dict[str, Any]] = []
    for username, c in sorted(candidates.items()):
        raw_graph_candidates.append(
            {
                "username": username,
                "instagram_id": c.instagram_id,
                "full_name": c.full_name,
                "followed_by_known_artists": sorted(c.followed_by_artists),
                "similar_to_known_artists": sorted(c.similar_to_artists),
                "followed_by_count": len(c.followed_by_artists),
                "similar_to_count": len(c.similar_to_artists),
                "evidence_count": c.evidence_count(),
            }
        )
        if username in existing_handles:
            prefiltered_rejected.append({"username": username, "reason": "already_in_database"})
            continue
        if c.evidence_count() < args.min_evidence:
            prefiltered_rejected.append(
                {
                    "username": username,
                    "reason": "below_evidence_threshold",
                    "evidence_count": c.evidence_count(),
                    "min_evidence": args.min_evidence,
                    "followed_by_known_artists": sorted(c.followed_by_artists),
                    "similar_to_known_artists": sorted(c.similar_to_artists),
                }
            )
            continue
        shortlisted[username] = c

    for c in shortlisted.values():
        payload = fetch_basic_profile(
            api_key,
            c.username,
            max_attempts=args.max_attempts,
            delay_seconds=args.delay,
        )
        if payload:
            c.merge_basic_profile(payload)
        time.sleep(max(0.0, args.delay))

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = list(prefiltered_rejected)
    created_ids: list[str] = []

    for username, c in sorted(shortlisted.items()):
        score, reasons = tattoo_confidence(c, min_followers=args.min_followers)
        row = {
            "username": username,
            "instagram_id": c.instagram_id,
            "full_name": c.full_name,
            "biography": c.biography,
            "follower_count": c.follower_count,
            "following_count": c.following_count,
            "media_count": c.media_count,
            "is_private": c.is_private,
            "is_verified": c.is_verified,
            "followed_by_known_artists": sorted(c.followed_by_artists),
            "similar_to_known_artists": sorted(c.similar_to_artists),
            "evidence_count": c.evidence_count(),
            "basic_profile_loaded": c.basic_profile_loaded,
            "score": round(score, 4),
            "score_reasons": reasons,
        }
        if score >= args.auto_create_threshold:
            accepted.append(row)
            if args.create_artists:
                out = to_artist_json(c)
                write_artist(username, out)
                created_ids.append(username)
                existing_handles.add(username)
        else:
            rejected.append({**row, "reason": "below_threshold"})

    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(accepted, f, indent=2, ensure_ascii=False)
    with open(RAW_GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_graph_candidates, f, indent=2, ensure_ascii=False)

    report = {
        "seed_count": len(seeds),
        "total_seed_count": total_seed_count,
        "start_seed_offset": start_seed_offset,
        "processed_seed_count": processed_seed_count,
        "next_seed_offset": min(total_seed_count, start_seed_offset + processed_seed_count),
        "all_seeds_processed": (start_seed_offset + processed_seed_count) >= total_seed_count,
        "candidate_count": len(candidates),
        "shortlisted_count": len(shortlisted),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "created_count": len(created_ids),
        "created_ids": created_ids,
        "rate_limited_seed_count": rate_limited_seeds,
        "following_requests_made": following_requests_made,
        "max_following_requests": args.max_following_requests,
        "stopped_due_to_following_cap": stopped_due_to_following_cap,
        "min_evidence": args.min_evidence,
        "min_followers": args.min_followers,
        "auto_create_threshold": args.auto_create_threshold,
        "raw_graph_path": str(RAW_GRAPH_PATH),
        "accepted": accepted,
        "rejected": rejected,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(
        "Done. "
        f"processed_seeds={processed_seed_count} next_offset={report['next_seed_offset']} "
        f"candidates={len(candidates)} shortlisted={len(shortlisted)} "
        f"accepted={len(accepted)} created={len(created_ids)} rejected={len(rejected)} "
        f"following_requests={following_requests_made}"
    )
    if report["all_seeds_processed"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
