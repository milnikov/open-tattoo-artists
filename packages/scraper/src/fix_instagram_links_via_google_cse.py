#!/usr/bin/env python3
"""
Fix `links.instagram` in data/artists/*.json using Google Custom Search.

Approach:
  1) Build query: "<artist name> instagram tattoo"
  2) Search top results
  3) Extract first Instagram profile link + handle from results
  4) If handle differs from stored `links.instagram`, update (optional)

Safety:
  - Uses token-overlap heuristic between artist name and the result's title/snippet.
  - Supports `--dry-run` and a JSONL review log for manual inspection.

Requirements:
  - Google Custom Search API enabled
  - Env vars:
      GOOGLE_CSE_API_KEY
      GOOGLE_CSE_CX
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


IG_URL_RE = re.compile(r"https?://(?:www\.)?instagram\.com/([^/?#]+)/?", re.IGNORECASE)
VALID_HANDLE_RE = re.compile(r"^[a-z0-9._]+$", re.IGNORECASE)

# Common noise tokens; keep it small to avoid over-filtering.
STOPWORDS = {
    "tattoo",
    "tattoos",
    "instagram",
    "the",
    "and",
    "studio",
    "tatto",
    "art",
    "artist",
    "workplace",
    "ink",
}


def normalize_handle_from_instagram_url(url: str | None) -> str | None:
    if not url:
        return None
    m = IG_URL_RE.search(url.strip())
    if not m:
        return None
    handle = (m.group(1) or "").strip().lower()
    if handle and VALID_HANDLE_RE.match(handle):
        return handle
    return None


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
    tokens = []
    for t in base.split(" "):
        t = t.strip(" -'\"").lower()
        if len(t) < 3:
            continue
        if t in STOPWORDS:
            continue
        tokens.append(t)
    # De-dupe while preserving order
    seen = set()
    out = []
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
    # Avoid overly generic artist names (e.g. "Aaron") → fall back to id/handle.
    if tokens and len(tokens) >= 2:
        base = " ".join(tokens[:4]).strip()
    else:
        base = (artist_id or stored_handle or name or "").strip()
    if not base:
        base = "tattoo artist"
    return f"{base} instagram tattoo"


def google_cse_search(api_key: str, cx: str, query: str, num: int) -> list[dict[str, Any]]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"q": query, "key": api_key, "cx": cx, "num": str(num)}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items") or []
    if not isinstance(items, list):
        return []
    return items[:num]


def extract_instagram_candidate_from_item(item: dict[str, Any]) -> tuple[str, str] | None:
    """
    Returns (handle, canonical_url) or None.
    Prefers `link` field; falls back to displayLink/title parsing.
    """
    for field in ("link", "formattedUrl", "htmlTitle"):
        raw = item.get(field)
        if isinstance(raw, str):
            m = IG_URL_RE.search(raw)
            if m:
                handle = (m.group(1) or "").strip().lower()
                if handle and VALID_HANDLE_RE.match(handle):
                    return handle, f"https://www.instagram.com/{handle}/"
    # Sometimes IG handle is visible as "@handle" in title/snippet.
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


def result_looks_like_artist(artist_tokens: list[str], item: dict[str, Any]) -> bool:
    if not artist_tokens:
        # If we can't tokenize artist name, don't block updates.
        return True
    hay = ""
    for f in ("title", "snippet", "htmlTitle"):
        v = item.get(f)
        if isinstance(v, str):
            hay += " " + v
    hay = hay.lower()
    if not hay.strip():
        return False
    # Require at least N tokens to appear in title/snippet.
    # (N is controlled outside via --min-token-match, but this function can
    # be used directly by checking how many tokens match.)
    matches = 0
    for t in artist_tokens:
        if t in hay:
            matches += 1
    return matches >= 1


def token_overlap_count(artist_tokens: list[str], item: dict[str, Any]) -> int:
    if not artist_tokens:
        return 0
    hay = ""
    for f in ("title", "snippet", "htmlTitle"):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix data/artists/*.json Instagram links via Google Custom Search.")
    parser.add_argument("--data-dir", default="data/artists", help="Artists directory (default: data/artists).")
    parser.add_argument("--limit", type=int, default=None, help="Max artists to process.")
    parser.add_argument("--start-index", type=int, default=0, help="Start offset (0-based).")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between queries (seconds).")
    parser.add_argument("--num", type=int, default=10, help="How many results to request from CSE.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes.")
    parser.add_argument("--only-different", action="store_true", help="Only act when stored instagram handle differs.")
    parser.add_argument("--min-token-match", type=int, default=1, help="Require at least N name tokens in title/snippet.")
    parser.add_argument(
        "--review-log",
        type=str,
        default="packages/scraper/instagram_link_fix_review.jsonl",
        help="JSONL file to append review entries.",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_CSE_API_KEY")
    cx = os.environ.get("GOOGLE_CSE_CX")
    if not api_key or not cx:
        print("Missing env vars: GOOGLE_CSE_API_KEY and GOOGLE_CSE_CX", file=sys.stderr)
        sys.exit(2)

    data_dir = repo_path(args.data_dir)
    if not data_dir.is_dir():
        print(f"data dir not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    review_path = repo_path(args.review_log)
    review_path.parent.mkdir(parents=True, exist_ok=True)

    all_files = sorted(data_dir.glob("*.json"), key=lambda p: p.stem)
    files = all_files[args.start_index : (args.start_index + args.limit) if args.limit is not None else None]

    processed = 0
    changed = 0

    for idx, p in enumerate(files, start=args.start_index):
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

        artist_tokens = split_artist_name_tokens(name)
        query = build_query(data)

        try:
            items = google_cse_search(api_key=api_key, cx=cx, query=query, num=args.num)
        except Exception as e:
            entry = {
                "artist_id": artist_id,
                "name": name,
                "query": query,
                "stored_instagram": stored_ig,
                "error": str(e),
            }
            with open(review_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            continue

        chosen = None
        # Pick the first IG result that passes safety heuristic.
        for item in items:
            cand = extract_instagram_candidate_from_item(item)
            if not cand:
                continue
            cand_handle, cand_url = cand
            if not cand_handle:
                continue
            # Token overlap safety check.
            overlap = token_overlap_count(artist_tokens, item)
            if overlap < args.min_token_match:
                continue
            chosen = {
                "handle": cand_handle,
                "url": cand_url,
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link"),
                "overlap_tokens": overlap,
            }
            break

        if not chosen:
            continue

        found_handle = chosen["handle"]
        if args.only_different and stored_handle and found_handle == stored_handle:
            continue

        if stored_handle == found_handle:
            # Either only-different is false, or stored handle missing; don't update.
            continue

        # Update
        if not args.dry_run:
            links = data.get("links") or {}
            data["links"] = links
            links["instagram"] = chosen["url"]
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed += 1

        # Always log the decision
        entry = {
            "artist_id": artist_id,
            "name": name,
            "query": query,
            "stored_instagram": stored_ig,
            "stored_handle": stored_handle,
            "chosen_handle": found_handle,
            "chosen_url": chosen["url"],
            "chosen_title": chosen.get("title"),
            "chosen_snippet": chosen.get("snippet"),
            "chosen_link": chosen.get("link"),
            "dry_run": args.dry_run,
            "changed": (not args.dry_run),
        }
        with open(review_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        time.sleep(args.sleep)

    print(f"Processed={processed} Changed={changed} DryRun={args.dry_run}")


if __name__ == "__main__":
    main()

