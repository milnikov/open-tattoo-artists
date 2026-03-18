#!/usr/bin/env python3
"""
Fix `links.instagram` in data/artists/*.json using SerpApi (Google Search results).

For each artist:
  - query: "<artist name> instagram tattoo"
  - take the first Instagram profile result from organic results
  - extract handle
  - if it differs from stored `links.instagram`, update it

Safety:
  - Uses a lightweight token-overlap heuristic between artist name tokens and the
    search result title/snippet.
  - Writes a JSONL review log of decisions.

Credentials:
  - Reads `SERPAPI_API_KEY` from environment.
  - If missing, attempts to load `packages/scraper/.env.local` (gitignored).
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
from urllib.parse import urlparse

import requests

from _repo_root import repo_path


VALID_HANDLE_RE = re.compile(r"^[a-z0-9._]+$", re.IGNORECASE)

# TattooFilter artist source pattern (used for slug-fallback risk filter)
TATTOOFILTER_SOURCE_RE = re.compile(
    r"^https?://(?:www\.)?tattoofilter\.com/artists/([^/?#]+)/?$",
    re.IGNORECASE,
)

# Instagram URL reserved first path segments that are NOT profile handles.
RESERVED_IG_SEGMENTS = {
    "p",
    "reel",
    "tv",
    "stories",
    "explore",
    "accounts",
    "direct",
    "about",
    "developer",
    "legal",
}

# Small set of common noise tokens (used in title/snippet overlap check)
STOPWORDS = {
    "tattoo",
    "tattoos",
    "instagram",
    "the",
    "and",
    "studio",
    "art",
    "artist",
    "workplace",
    "ink",
}


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs into os.environ (does not override existing vars)."""
    try:
        raw = path.read_text("utf-8")
    except Exception:
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if k and k not in os.environ:
            os.environ[k] = v


def extract_profile_handle_from_instagram_url(url: str | None) -> str | None:
    """
    Extract Instagram profile handle from a URL like:
      https://www.instagram.com/<handle>/
    Rejects non-profile URLs like:
      /p/<shortcode>, /reel/<shortcode>, /explore/, etc.
    """
    if not url:
        return None

    u = urlparse(url.strip())
    host = (u.netloc or "").lower()
    if not (host.endswith("instagram.com")):
        return None

    # Path like "/<handle>/" => one segment. Anything else => reject.
    segments = [s for s in (u.path or "").split("/") if s]
    if len(segments) != 1:
        return None
    handle = segments[0].strip().lower()
    if not handle or handle in RESERVED_IG_SEGMENTS:
        return None
    if VALID_HANDLE_RE.match(handle):
        return handle
    return None


def normalize_handle_from_instagram_url(url: str | None) -> str | None:
    return extract_profile_handle_from_instagram_url(url)


def split_artist_name_tokens(name: str) -> list[str]:
    if not name:
        return []
    # Common separators: "·", "|", etc.
    base = re.split(r"[|·•]", name, maxsplit=1)[0]
    base = base.strip()
    base = re.sub(r"@[\w.]+", " ", base)  # remove mentions
    base = re.sub(r"[^a-zA-Z0-9\s\-']", " ", base)
    base = re.sub(r"\s+", " ", base).strip().lower()
    if not base:
        return []
    tokens: list[str] = []
    for t in base.split(" "):
        t = t.strip(" -'\"").lower()
        if len(t) < 3:
            continue
        if t in STOPWORDS:
            continue
        tokens.append(t)
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_query(artist: dict[str, Any]) -> str:
    name = (artist.get("name") or "").strip()
    artist_id = (artist.get("id") or "").strip()
    links = artist.get("links") or {}
    stored_instagram = links.get("instagram")
    stored_handle = normalize_handle_from_instagram_url(stored_instagram) if isinstance(stored_instagram, str) else None

    tokens = split_artist_name_tokens(name)

    # If the name is too generic (e.g. "Aaron"), it causes ambiguous results.
    # In that case, prefer the artist_id / stored handle in the query.
    if tokens and len(tokens) >= 2:
        base = " ".join(tokens[:4]).strip()
    else:
        base = (artist_id or stored_handle or name or "").strip()

    if not base:
        base = "tattoo artist"

    loc = artist.get("location") or {}
    city = (loc.get("city") or "").strip()
    country = (loc.get("country") or "").strip()

    # Use site restriction to reduce non-profile noise in organic results.
    # Location is optional: include only when it looks meaningful.
    loc_part = ""
    if city and city.lower() not in ("unknown",) and len(city) >= 4:
        loc_part = f" {city}"
    elif country and country.lower() not in ("unknown",) and len(country) >= 4:
        loc_part = f" {country}"

    # Note: "instagram" term is redundant when using site:instagram.com.
    return f"site:instagram.com {base}{loc_part} tattoo"


def _haystack_title_snippet(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for f in ("title", "snippet"):
        v = item.get(f)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return " ".join(parts).strip().lower()


def score_candidate(
    artist_tokens: list[str],
    item: dict[str, Any],
    cand_handle: str,
) -> tuple[int, int]:
    """
    Return a score tuple:
      (overlap_tokens, handle_mentioned_flag)
    Higher is better.
    """
    overlap = token_overlap_count(artist_tokens, item)
    hay = _haystack_title_snippet(item)
    handle_mentioned = 0
    if cand_handle:
        if f"@{cand_handle}" in hay or f"instagram.com/{cand_handle}" in hay:
            handle_mentioned = 1
    return (overlap, handle_mentioned)


def serpapi_search(api_key: str, query: str, num: int) -> list[dict[str, Any]]:
    """
    Returns SerpApi organic results list.
    """
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": str(num),
        "hl": "en",
    }
    resp = requests.get(url, params=params, timeout=40)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("organic_results") or []
    if not isinstance(items, list):
        return []
    return items


def extract_instagram_candidate_from_item(item: dict[str, Any]) -> tuple[str, str] | None:
    """
    Return (handle, canonical_url) or None.
    Uses `link`/`formattedUrl` only if it's a *profile* URL; otherwise falls back to '@handle' in title/snippet.
    """
    for field in ("link", "formattedUrl"):
        raw = item.get(field)
        if not isinstance(raw, str):
            continue
        handle = extract_profile_handle_from_instagram_url(raw)
        if handle:
            return handle, f"https://www.instagram.com/{handle}/"

    for field in ("title", "snippet"):
        raw = item.get(field)
        if not isinstance(raw, str):
            continue
        m = re.search(r"@([a-z0-9._]{2,30})", raw, flags=re.IGNORECASE)
        if m:
            handle = (m.group(1) or "").strip().lower()
            if handle and VALID_HANDLE_RE.match(handle):
                return handle, f"https://www.instagram.com/{handle}/"
    return None


def token_overlap_count(artist_tokens: list[str], item: dict[str, Any]) -> int:
    if not artist_tokens:
        return 0
    hay = ""
    for f in ("title", "snippet"):
        v = item.get(f)
        if isinstance(v, str):
            hay += " " + v
    hay = hay.lower()
    if not hay.strip():
        return 0
    c = 0
    for t in artist_tokens:
        if t in hay:
            c += 1
    return c


def is_high_risk_slug_fallback_artist(data: dict[str, Any]) -> bool:
    """
    Heuristic:
      - links.source is a TattooFilter artist URL
      - links.instagram equals the TattooFilter slug (slug fallback)
    """
    links = data.get("links") or {}
    source = links.get("source") or ""
    ig = links.get("instagram")

    m = TATTOOFILTER_SOURCE_RE.match(str(source).strip())
    if not m:
        return False
    slug = (m.group(1) or "").strip().lower()
    if not slug:
        return False

    stored_handle = normalize_handle_from_instagram_url(ig) if isinstance(ig, str) else None
    if not stored_handle:
        return False
    return stored_handle.lower() == slug.lower()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix artist IG links via SerpApi.")
    parser.add_argument("--data-dir", default="data/artists", help="Artists directory (default: data/artists).")
    parser.add_argument("--limit", type=int, default=None, help="Max artists to process.")
    parser.add_argument("--start-index", type=int, default=0, help="Start offset (0-based).")
    parser.add_argument(
        "--only-artist-id",
        type=str,
        default=None,
        help="Only process one artist JSON by id (e.g. aaronsprings).",
    )
    parser.add_argument("--sleep", type=float, default=0.3, help="Delay between queries (seconds).")
    parser.add_argument("--num", type=int, default=10, help="How many organic results to request.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes.")
    parser.add_argument("--only-different", action="store_true", help="Only act when handle differs.")
    parser.add_argument("--min-token-match", type=int, default=1, help="Require at least N name tokens match title/snippet.")
    parser.add_argument(
        "--require-handle-mentioned",
        action="store_true",
        help="Require that the chosen IG handle is mentioned in title/snippet (higher precision).",
    )
    parser.add_argument(
        "--only-high-risk-slug-fallback",
        action="store_true",
        help="Only process TattooFilter-sourced artists where links.instagram equals the TattooFilter slug (common fallback error).",
    )
    parser.add_argument(
        "--review-log",
        type=str,
        default="packages/scraper/instagram_link_fix_review_serpapi.jsonl",
        help="JSONL file to append review entries.",
    )
    args = parser.parse_args()

    # Load env file as fallback (gitignored, should be safe locally)
    env_local = repo_path("packages", "scraper", ".env.local")
    load_env_file(env_local)

    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        print("Missing SERPAPI_API_KEY (env var) and packages/scraper/.env.local.", file=sys.stderr)
        sys.exit(2)

    data_dir = repo_path(args.data_dir)
    if not data_dir.is_dir():
        print(f"data dir not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    review_path = repo_path(args.review_log)
    review_path.parent.mkdir(parents=True, exist_ok=True)

    all_files = sorted(data_dir.glob("*.json"), key=lambda p: p.stem)
    if args.only_artist_id:
        p = data_dir / f"{args.only_artist_id}.json"
        if not p.exists():
            print(f"Artist not found: {p}", file=sys.stderr)
            sys.exit(1)
        files = [p]
    else:
        files = all_files[args.start_index : (args.start_index + args.limit) if args.limit is not None else None]

    processed = 0
    changed = 0

    for p in files:
        processed += 1
        artist_id = p.stem
        try:
            data = json.loads(p.read_text("utf-8"))
        except Exception:
            continue

        name = (data.get("name") or "").strip()
        links = data.get("links") or {}
        stored_ig = links.get("instagram")
        stored_handle = normalize_handle_from_instagram_url(stored_ig) if stored_ig else None

        if args.only_high_risk_slug_fallback:
            if not is_high_risk_slug_fallback_artist(data):
                continue

        artist_tokens = split_artist_name_tokens(name)
        query = build_query(data)

        try:
            items = serpapi_search(api_key=api_key, query=query, num=args.num)
        except Exception as e:
            with open(review_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "artist_id": artist_id,
                    "name": name,
                    "query": query,
                    "stored_instagram": stored_ig,
                    "error": str(e),
                }, ensure_ascii=False) + "\n")
            continue

        best = None
        best_score: tuple[int, int] | None = None

        for item in items:
            cand = extract_instagram_candidate_from_item(item)
            if not cand:
                continue
            cand_handle, cand_url = cand

            overlap = token_overlap_count(artist_tokens, item)
            if overlap < args.min_token_match:
                continue

            s = score_candidate(artist_tokens, item, cand_handle=cand_handle)
            if best_score is None or s > best_score:
                best_score = s
                best = {
                    "handle": cand_handle,
                    "url": cand_url,
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "overlap_tokens": overlap,
                    "score_overlap": s[0],
                    "score_handle_mentioned": s[1],
                }

        chosen = best
        if not chosen:
            continue

        if args.require_handle_mentioned and chosen.get("score_handle_mentioned") != 1:
            continue

        found_handle = chosen["handle"]
        if args.only_different and stored_handle and found_handle == stored_handle:
            continue

        if stored_handle == found_handle:
            continue

        if not args.dry_run:
            links = data.get("links") or {}
            data["links"] = links
            links["instagram"] = chosen["url"]
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed += 1

        # Always log the decision (including dry-run)
        with open(review_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "artist_id": artist_id,
                "name": name,
                "query": query,
                "stored_instagram": stored_ig,
                "stored_handle": stored_handle,
                "chosen_handle": found_handle,
                "chosen_url": chosen["url"],
                "chosen_title": chosen.get("title"),
                "chosen_snippet": chosen.get("snippet"),
                "dry_run": args.dry_run,
            }, ensure_ascii=False) + "\n")

        time.sleep(args.sleep)

    print(f"Processed={processed} Changed={changed} DryRun={args.dry_run}")


if __name__ == "__main__":
    main()

