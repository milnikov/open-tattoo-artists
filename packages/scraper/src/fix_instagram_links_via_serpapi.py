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
import unicodedata
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

# Tokens matched in Serp title/snippet that usually aren't a person's name — don't use alone
# to inflate identity (studio addresses, generic service words).
DISPLAY_NAME_NOISE = frozenset({
    "custom",
    "tattoos",
    "tattoo",
    "traditional",
    "realism",
    "blackwork",
    "denver",
    "studio",
    "gallery",
    "shop",
    "company",
    "llc",
    "inc",
})


def fold_text_for_match(s: str) -> str:
    """
    Lowercase ASCII fold for substring checks: unicode stylistic letters (e.g. bold 𝗠𝗲𝗴𝗮𝗻)
    become plain letters so name tokens from JSON match Google's title/snippet.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _compact_alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def handle_identity_score(handle: str, artist_id: str, artist_tokens: list[str]) -> int:
    """
    Estimate how strongly an Instagram handle looks tied to the artist identity.
    Higher score => stronger identity match.
    """
    h_compact = _compact_alnum(handle)
    if not h_compact:
        return 0

    score = 0
    aid_compact = _compact_alnum(artist_id)
    if aid_compact:
        if aid_compact == h_compact:
            score += 5
        elif aid_compact in h_compact or h_compact in aid_compact:
            score += 3

    for t in artist_tokens:
        tt = _compact_alnum(t)
        if not tt or len(tt) < 3:
            continue
        if tt in h_compact:
            score += 2

    return score


def looks_like_aggregator_handle(handle: str) -> bool:
    h = (handle or "").lower()
    bad_markers = (
        "tattooartists",
        "magazine",
        "features",
        "feature",
        "repost",
        "news",
        "daily",
    )
    return any(m in h for m in bad_markers)


def load_id_set_from_file(path: Path) -> set[str]:
    """Load artist IDs from JSON array or one id per line."""
    raw = path.read_text("utf-8").strip()
    if not raw:
        return set()
    if raw.startswith("["):
        data = json.loads(raw)
        return {str(x) for x in data if x}
    return {line.strip() for line in raw.splitlines() if line.strip()}


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


def slug_word_tokens(artist_id: str) -> list[str]:
    """
    Words from the JSON `id`/slug (underscores, dots, etc.) for overlap checks when
    `name` is a studio label and does not contain the person's real name tokens.
    """
    if not artist_id:
        return []
    parts = re.split(r"[^a-z0-9]+", artist_id.lower())
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) < 3 or p in STOPWORDS:
            continue
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def artist_tokens_for_serp_match(name: str, artist_id: str) -> list[str]:
    """Name tokens plus slug words, useful for Serp title/snippet overlap."""
    seen: set[str] = set()
    out: list[str] = []
    for t in split_artist_name_tokens(name) + slug_word_tokens(artist_id):
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

    # Note: "instagram" term is redundant when using site:instagram.com.
    # Location (city/country) is intentionally omitted — it skews Serp toward local
    # shops and away from the artist’s actual handle.
    return f"site:instagram.com {base} tattoo"


def _haystack_title_snippet(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for f in ("title", "snippet"):
        v = item.get(f)
        if isinstance(v, str) and v.strip():
            parts.append(v)
    return fold_text_for_match(" ".join(parts))


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


def extract_instagram_candidate_from_item(item: dict[str, Any]) -> tuple[str, str, str] | None:
    """
    Return (handle, canonical_url, source) or None.
    source is:
      - "profile_link" when extracted from profile URL in result link/formattedUrl
      - "mention" when extracted from @handle in title/snippet
    Uses `link`/`formattedUrl` only if it's a *profile* URL; otherwise falls back to '@handle' in title/snippet.
    """
    for field in ("link", "formattedUrl"):
        raw = item.get(field)
        if not isinstance(raw, str):
            continue
        handle = extract_profile_handle_from_instagram_url(raw)
        if handle:
            return handle, f"https://www.instagram.com/{handle}/", "profile_link"

    for field in ("title", "snippet"):
        raw = item.get(field)
        if not isinstance(raw, str):
            continue
        m = re.search(r"@([a-z0-9._]{2,30})", raw, flags=re.IGNORECASE)
        if m:
            handle = (m.group(1) or "").strip().lower()
            if handle and VALID_HANDLE_RE.match(handle):
                return handle, f"https://www.instagram.com/{handle}/", "mention"
    return None


def token_overlap_count(artist_tokens: list[str], item: dict[str, Any]) -> int:
    if not artist_tokens:
        return 0
    hay = ""
    for f in ("title", "snippet"):
        v = item.get(f)
        if isinstance(v, str):
            hay += " " + v
    hay = fold_text_for_match(hay)
    if not hay.strip():
        return 0
    c = 0
    for t in artist_tokens:
        if t in hay:
            c += 1
    return c


def person_name_token_overlap_in_serp(
    artist_tokens: list[str],
    title: str | None,
    snippet: str | None,
) -> int:
    """
    Count name tokens (len>=4, not DISPLAY_NAME_NOISE) present in folded Serp text.
    Reduces false boosts from "Custom … Denver" style display names.
    """
    hay = fold_text_for_match(" ".join(x for x in (title or "", snippet or "") if x))
    if not hay.strip():
        return 0
    n = 0
    for t in artist_tokens:
        if len(t) < 4 or t in DISPLAY_NAME_NOISE:
            continue
        if t in hay:
            n += 1
    return n


def conservative_serp_quality_bypass(
    chosen: dict[str, Any],
    found_handle: str,
    min_token_match: int,
    artist_tokens: list[str] | None = None,
) -> bool:
    """
    When the handle barely scores via slug/name heuristics, still allow conservative
    replacement if the organic result looks like a real IG profile card and the
    artist name tokens overlap the title/snippet, with @handle visible there.

    If artist_tokens is passed, require at least one non-noise person-name token in the
    Serp fields when overlap would otherwise come only from generic studio words.
    """
    pseudo_item = {"title": chosen.get("title"), "snippet": chosen.get("snippet")}
    overlap_ok = (chosen.get("overlap_tokens") or 0) >= min_token_match
    if (
        artist_tokens
        and overlap_ok
        and not person_name_token_overlap_in_serp(
            artist_tokens,
            chosen.get("title") if isinstance(chosen.get("title"), str) else None,
            chosen.get("snippet") if isinstance(chosen.get("snippet"), str) else None,
        )
    ):
        overlap_ok = False
    return (
        chosen.get("source") == "profile_link"
        and title_looks_like_profile(pseudo_item, found_handle)
        and overlap_ok
        and chosen.get("score_handle_mentioned") == 1
    )


def title_looks_like_profile(item: dict[str, Any], handle: str) -> bool:
    """
    Heuristic: organic result title resembles an Instagram profile card/snippet.
    Examples:
      - "Name (@handle) • Instagram photos and videos"
      - "@handle • Instagram photos and videos"
      - "handle"
    """
    title = item.get("title")
    if not isinstance(title, str):
        return False
    t = fold_text_for_match(title.strip())
    h = (handle or "").strip().lower()
    if not t or not h:
        return False
    if "instagram photos and videos" in t:
        return True
    if f"(@{h})" in t or f"@{h}" in t:
        return True
    if t == h or t == f"@{h}":
        return True
    return False


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
    parser.add_argument(
        "--only-ids-file",
        type=str,
        default=None,
        help="Only process artist IDs listed here (JSON array or one per line). "
        "e.g. from list_hidden_artists.py --output.",
    )
    parser.add_argument("--sleep", type=float, default=0.3, help="Delay between queries (seconds).")
    parser.add_argument("--num", type=int, default=10, help="How many organic results to request.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes.")
    parser.add_argument(
        "--only-different",
        action="store_true",
        help="Deprecated: no-op. Rows where Serp's handle matches stored are skipped automatically.",
    )
    parser.add_argument("--min-token-match", type=int, default=1, help="Require at least N name tokens match title/snippet.")
    parser.add_argument(
        "--require-handle-mentioned",
        action="store_true",
        help="Require that the chosen IG handle is mentioned in title/snippet (higher precision).",
    )
    parser.add_argument(
        "--profile-link-only",
        action="store_true",
        help="Only accept candidates extracted from Instagram profile links (skip @mention-only candidates).",
    )
    parser.add_argument(
        "--require-profile-title",
        action="store_true",
        help="Require result title to look like an Instagram profile card/snippet for the chosen handle.",
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
    parser.add_argument(
        "--conservative-replace-mode",
        action="store_true",
        help="Only replace when candidate identity match is strong; skip uncertain rows.",
    )
    parser.add_argument(
        "--min-identity-score",
        type=int,
        default=2,
        help="Minimum candidate identity score for --conservative-replace-mode (default: 2). "
        "Below this, a stricter Serp quality bypass may still allow profile_link rows.",
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
        if args.only_ids_file:
            print("Cannot use both --only-artist-id and --only-ids-file.", file=sys.stderr)
            sys.exit(2)
        p = data_dir / f"{args.only_artist_id}.json"
        if not p.exists():
            print(f"Artist not found: {p}", file=sys.stderr)
            sys.exit(1)
        files = [p]
    else:
        files = all_files
        if args.only_ids_file:
            only_path = (
                Path(args.only_ids_file)
                if Path(args.only_ids_file).is_absolute()
                else repo_path(args.only_ids_file)
            )
            if not only_path.is_file():
                print(f"only-ids-file not found: {only_path}", file=sys.stderr)
                sys.exit(1)
            only_ids = load_id_set_from_file(only_path)
            files = [p for p in all_files if p.stem in only_ids]
            print(f"Restricting to {len(files)} artist files (from {len(only_ids)} IDs in {only_path})")
        files = files[args.start_index : (args.start_index + args.limit) if args.limit is not None else None]

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
            cand_handle, cand_url, cand_source = cand
            if args.profile_link_only and cand_source != "profile_link":
                continue

            overlap = token_overlap_count(artist_tokens, item)
            if overlap < args.min_token_match:
                continue

            if args.require_profile_title and not title_looks_like_profile(item, cand_handle):
                continue

            s = score_candidate(artist_tokens, item, cand_handle=cand_handle)
            if best_score is None or s > best_score:
                best_score = s
                best = {
                    "handle": cand_handle,
                    "url": cand_url,
                    "source": cand_source,
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
        candidate_identity = handle_identity_score(found_handle, artist_id, artist_tokens)
        stored_identity = handle_identity_score(stored_handle or "", artist_id, artist_tokens)

        # No-op: avoid conservative false-positives and duplicate review noise when
        # Serp agrees with the URL we already store.
        if stored_handle and found_handle == stored_handle:
            continue

        pseudo_pick = {"title": chosen.get("title"), "snippet": chosen.get("snippet")}
        person_ov = person_name_token_overlap_in_serp(
            artist_tokens,
            chosen.get("title") if isinstance(chosen.get("title"), str) else None,
            chosen.get("snippet") if isinstance(chosen.get("snippet"), str) else None,
        )
        if (
            title_looks_like_profile(pseudo_pick, found_handle)
            and chosen.get("score_handle_mentioned") == 1
            and person_ov >= 1
        ):
            # Brand handles often score 0 from slug/name alone though the Serp card names the person.
            candidate_identity = max(candidate_identity, args.min_identity_score)

        identity_bypass = False
        if args.conservative_replace_mode:
            skip_reason = None
            identity_ok = candidate_identity >= args.min_identity_score
            if not identity_ok and conservative_serp_quality_bypass(
                chosen, found_handle, args.min_token_match, artist_tokens=artist_tokens
            ):
                identity_ok = True
                identity_bypass = True

            if not identity_ok:
                skip_reason = "candidate_identity_too_low"
            # Reject ties: replacing with an equally plausible handle is usually ambiguous.
            elif stored_handle and stored_identity >= candidate_identity:
                skip_reason = "stored_identity_not_weaker"
            elif looks_like_aggregator_handle(found_handle):
                skip_reason = "aggregator_like_candidate"

            if skip_reason:
                with open(review_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps({
                        "artist_id": artist_id,
                        "name": name,
                        "query": query,
                        "stored_instagram": stored_ig,
                        "stored_handle": stored_handle,
                        "stored_identity_score": stored_identity,
                        "candidate_handle": found_handle,
                        "candidate_identity_score": candidate_identity,
                        "candidate_title": chosen.get("title"),
                        "candidate_snippet": chosen.get("snippet"),
                        "skipped_by_conservative_mode": True,
                        "skip_reason": skip_reason,
                        "dry_run": args.dry_run,
                    }, ensure_ascii=False) + "\n")
                continue

        if not args.dry_run:
            links = data.get("links") or {}
            data["links"] = links
            links["instagram"] = chosen["url"]
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed += 1

        # Always log the decision (including dry-run)
        log_entry: dict[str, Any] = {
            "artist_id": artist_id,
            "name": name,
            "query": query,
            "stored_instagram": stored_ig,
            "stored_handle": stored_handle,
            "stored_identity_score": stored_identity,
            "chosen_handle": found_handle,
            "chosen_identity_score": candidate_identity,
            "chosen_url": chosen["url"],
            "chosen_source": chosen.get("source"),
            "chosen_title": chosen.get("title"),
            "chosen_snippet": chosen.get("snippet"),
            "dry_run": args.dry_run,
        }
        if identity_bypass:
            log_entry["conservative_identity_serp_bypass"] = True
        with open(review_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        time.sleep(args.sleep)

    print(f"Processed={processed} Changed={changed} DryRun={args.dry_run}")


if __name__ == "__main__":
    main()

