#!/usr/bin/env python3
"""
Apply `links.instagram` updates from an existing fix_instagram_links_via_serpapi JSONL
review log — no SerpApi calls.

For each artist, uses the last non-error row in the log (optionally limited to a
1-based line range inside the JSONL), then re-checks against **current** artist JSON
with relaxed-but-safe heuristics: slug + display-name overlap, profile-shaped titles,
and junk placeholders (gmail.com, etc.).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCR_DIR = Path(__file__).resolve().parent
if str(_SCR_DIR) not in sys.path:
    sys.path.insert(0, str(_SCR_DIR))

from fix_instagram_links_via_serpapi import (  # noqa: E402
    artist_tokens_for_serp_match,
    conservative_serp_quality_bypass,
    extract_profile_handle_from_instagram_url,
    fold_text_for_match,
    handle_identity_score,
    looks_like_aggregator_handle,
    person_name_token_overlap_in_serp,
    score_candidate,
    slug_word_tokens,
    split_artist_name_tokens,
    token_overlap_count,
    title_looks_like_profile,
)
from _repo_root import repo_path  # noqa: E402

# Stored handles that are obvious placeholder / scrape errors — always allow replacement
# when Serp shows a normal profile card for the artist.
JUNK_STORED_HANDLES = frozenset({
    "gmail.com",
    "naver.com",
    "hotmail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "outlook.com",
    "icloud.com",
    "protonmail.com",
    "aol.com",
    "yandex.com",
    "tattoo.",
})


def _log_identity_score(row: dict[str, Any]) -> int:
    for k in ("chosen_identity_score", "candidate_identity_score"):
        v = row.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0
    return 0


# Curated from offline dry-runs: Serp “profile” rows that point at shops, reposts, or the wrong person.
OFFLINE_CANDIDATE_DENYLIST = frozenset({
    "kzzkzz_",
    "instabubuh",
    "hectorfong",
    "hamishclarke_",
    "raccoonfoo",
    "purinto_art",
    "angellotarot",
    "pablodelarue",
    "ksucheriddle",
    "shwabbles",
    "ha_haha_haha_ha_",
    "nachoo1313",
    "t_diary",
    "alter_schwan",
})


def is_questionable_bulk_ig_handle(fh: str) -> bool:
    """
    Drop Serp candidates that usually point at shops, promos, or non-artist accounts
    when replaying offline (conservative).
    """
    h = (fh or "").lower()
    needles = (
        "gallery",
        "tatshop",
        "homeless",
        "movies",
        "lisson",
        "333company",
        "levifweekend",
        "fraktmovement",
        "mercwith",
        "world.oftattoo",
    )
    return any(n in h for n in needles)


def is_junk_stored_handle(h: str | None) -> bool:
    if not h:
        return True
    hl = h.strip().lower().rstrip(".")
    if hl in JUNK_STORED_HANDLES:
        return True
    if hl.endswith(".com") and any(x in hl for x in ("gmail", "naver", "yahoo", "hotmail", "outlook")):
        return True
    return False


def _load_latest_rows(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if o.get("error"):
                continue
            aid = o.get("artist_id")
            if isinstance(aid, str) and aid:
                latest[aid] = o
    return latest


def _load_latest_rows_in_line_range(path: Path, first_line: int, last_line: int) -> dict[str, dict[str, Any]]:
    """
    Like `_load_latest_rows` but only reads JSONL lines in [first_line, last_line] (1-based, inclusive).
    Later lines in that window win for a given artist_id.
    """
    latest: dict[str, dict[str, Any]] = {}
    if first_line < 1 or last_line < first_line:
        return latest
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if i > last_line:
                break
            if i < first_line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("error"):
                continue
            aid = o.get("artist_id")
            if isinstance(aid, str) and aid:
                latest[aid] = o
    return latest


def _row_target(row: dict[str, Any]) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Return (found_handle, chosen_url_or_none, title, snippet).
    """
    if row.get("skipped_by_conservative_mode"):
        h = row.get("candidate_handle")
        return (
            h if isinstance(h, str) else None,
            None,
            row.get("candidate_title") if isinstance(row.get("candidate_title"), str) else None,
            row.get("candidate_snippet") if isinstance(row.get("candidate_snippet"), str) else None,
        )
    url = row.get("chosen_url")
    h = row.get("chosen_handle")
    if isinstance(url, str) and url.strip():
        uh = extract_profile_handle_from_instagram_url(url)
        if h and isinstance(h, str) and uh and uh != h.lower():
            # rare mismatch — trust URL
            h = uh
        elif not h and uh:
            h = uh
    return (
        h if isinstance(h, str) else None,
        url if isinstance(url, str) else None,
        row.get("chosen_title") if isinstance(row.get("chosen_title"), str) else None,
        row.get("chosen_snippet") if isinstance(row.get("chosen_snippet"), str) else None,
    )


def _chosen_dict_for_bypass(
    row: dict[str, Any],
    found_handle: str,
    title: str | None,
    snippet: str | None,
    artist_tokens: list[str],
) -> dict[str, Any]:
    pseudo = {"title": title, "snippet": snippet}
    overlap = token_overlap_count(artist_tokens, pseudo)
    mention = score_candidate(artist_tokens, pseudo, cand_handle=found_handle)[1]
    src: str | None = row.get("chosen_source") if isinstance(row.get("chosen_source"), str) else None
    if not src:
        if title_looks_like_profile(pseudo, found_handle):
            src = "profile_link"
        else:
            src = "mention"
    return {
        "title": title,
        "snippet": snippet,
        "source": src,
        "overlap_tokens": overlap,
        "score_handle_mentioned": mention,
    }


def slug_overlap_in_serp(artist_id: str, title: str | None, snippet: str | None) -> int:
    hay = fold_text_for_match(" ".join(x for x in (title or "", snippet or "") if x))
    if not hay.strip():
        return 0
    n = 0
    for t in slug_word_tokens(artist_id):
        if len(t) < 3:
            continue
        if t in hay:
            n += 1
    return n


def strong_serp_signals(
    name: str,
    artist_id: str,
    fh: str,
    title: str | None,
    snippet: str | None,
) -> bool:
    """
    Profile-shaped title, @handle in folded text, and corroboration either from
    (a) two distinct display-name tokens or (b) slug words in the Serp text.

    We deliberately do *not* treat generic token_overlap or a single first-name hit
    as enough — that pattern false-positives wrong profiles (e.g. same first name).
    """
    artist_tokens = artist_tokens_for_serp_match(name, artist_id)
    pseudo = {"title": title, "snippet": snippet}
    if not isinstance(title, str) or not title.strip():
        return False
    if not title_looks_like_profile(pseudo, fh):
        return False
    if score_candidate(artist_tokens, pseudo, cand_handle=fh)[1] != 1:
        return False
    name_only = split_artist_name_tokens(name)
    person_fn = person_name_token_overlap_in_serp(name_only, title, snippet)
    s_ov = slug_overlap_in_serp(artist_id, title, snippet)
    return bool(person_fn >= 2 or s_ov >= 1)


def passes_relaxed_conservative(
    *,
    artist_id: str,
    name: str,
    stored_handle: str | None,
    found_handle: str,
    row: dict[str, Any],
    title: str | None,
    snippet: str | None,
    min_identity_score: int,
    min_token_match: int,
) -> tuple[bool, str, bool]:
    """
    Return (ok, reason_if_fail, strong_serp_ok).

    `strong_serp_ok`: profile card + @handle + name/slug overlap — used to allow
    replacing equal-identity handles (e.g. wrong handle with same rough score).
    """
    fh = found_handle.strip().lower()
    if looks_like_aggregator_handle(fh):
        return False, "aggregator_like_candidate", False
    if fh in OFFLINE_CANDIDATE_DENYLIST:
        return False, "offline_candidate_denylist", False
    if is_questionable_bulk_ig_handle(fh):
        return False, "questionable_candidate_handle", False

    artist_tokens = artist_tokens_for_serp_match(name, artist_id)
    candidate_identity = handle_identity_score(fh, artist_id, artist_tokens)
    stored_identity = handle_identity_score((stored_handle or "").lower(), artist_id, artist_tokens)

    pseudo = {"title": title, "snippet": snippet}
    person_fn_only = person_name_token_overlap_in_serp(split_artist_name_tokens(name), title, snippet)
    slug_ov = slug_overlap_in_serp(artist_id, title, snippet)
    strong = strong_serp_signals(name, artist_id, fh, title, snippet)
    if (
        title_looks_like_profile(pseudo, fh)
        and score_candidate(artist_tokens, pseudo, cand_handle=fh)[1] == 1
        and (person_fn_only >= 2 or slug_ov >= 1)
    ):
        candidate_identity = max(candidate_identity, min_identity_score)

    chosen = _chosen_dict_for_bypass(row, fh, title, snippet, artist_tokens)

    identity_ok = candidate_identity >= min_identity_score
    if not identity_ok and conservative_serp_quality_bypass(
        chosen, fh, min_token_match, artist_tokens=artist_tokens
    ):
        identity_ok = True

    if not identity_ok:
        return False, "candidate_identity_too_low", strong

    junk = is_junk_stored_handle(stored_handle)

    if stored_handle and fh != stored_handle and stored_identity > candidate_identity and not junk:
        # Allow override when Serp strongly matches slug/name (studio vs personal handle, etc.)
        if not (strong and candidate_identity >= min_identity_score):
            return False, "stored_identity_stronger", strong

    if (
        stored_handle
        and fh != stored_handle
        and stored_identity == candidate_identity
        and stored_identity > 0
        and not junk
    ):
        # Ambiguous tie: only replace with an explicit profile+overlap confirmation.
        if not strong:
            return False, "stored_identity_tie", strong

    return True, "", strong


def success_row_extra_gate(
    row: dict[str, Any],
    *,
    artist_id: str,
    name: str,
    found_handle: str,
    title: str | None,
    snippet: str | None,
    min_identity_score: int,
) -> bool:
    """
    Backfill rows where the log says dry_run false but the JSON was never updated.
    Without chosen_identity_score (older logs), require stronger title/snippet match.
    """
    if row.get("skipped_by_conservative_mode"):
        return True
    cis = row.get("chosen_identity_score")
    if cis is not None:
        return int(cis) >= min_identity_score
    pseudo = {"title": title, "snippet": snippet}
    tokens = split_artist_name_tokens(name)
    overlap = token_overlap_count(tokens, pseudo)
    if overlap < 2:
        return False
    if not title_looks_like_profile(pseudo, found_handle):
        return False
    return score_candidate(tokens, pseudo, cand_handle=found_handle)[1] == 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply IG links from existing SerpApi review JSONL (no API calls).")
    parser.add_argument(
        "--review-log",
        default="packages/scraper/instagram_link_fix_review_serpapi.jsonl",
        help="Path to JSONL (repo-relative or absolute).",
    )
    parser.add_argument("--data-dir", default="data/artists", help="Artists directory under repo root.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned updates only.")
    parser.add_argument("--min-identity-score", type=int, default=2)
    parser.add_argument("--min-token-match", type=int, default=1)
    parser.add_argument(
        "--jsonl-first-line",
        type=int,
        default=None,
        help="If set with --jsonl-last-line, only consider artists appearing on these 1-based JSONL lines (inclusive).",
    )
    parser.add_argument(
        "--jsonl-last-line",
        type=int,
        default=None,
        help="See --jsonl-first-line.",
    )
    args = parser.parse_args()

    log_path = Path(args.review_log) if Path(args.review_log).is_absolute() else repo_path(args.review_log)
    data_dir = repo_path(args.data_dir)

    if not log_path.is_file():
        print(f"Review log not found: {log_path}", file=sys.stderr)
        sys.exit(1)

    if args.jsonl_first_line is not None or args.jsonl_last_line is not None:
        if args.jsonl_first_line is None or args.jsonl_last_line is None:
            print("Both --jsonl-first-line and --jsonl-last-line are required together.", file=sys.stderr)
            sys.exit(2)
        latest = _load_latest_rows_in_line_range(log_path, args.jsonl_first_line, args.jsonl_last_line)
    else:
        latest = _load_latest_rows(log_path)
    planned: list[tuple[str, str | None, str, str, str]] = []  # id, old_h, new_h, url, note

    for artist_id, row in sorted(latest.items()):
        path = data_dir / f"{artist_id}.json"
        if not path.is_file():
            continue

        found_handle, chosen_url, title, snippet = _row_target(row)
        if not found_handle:
            continue
        fh = found_handle.strip().lower()

        data = json.loads(path.read_text(encoding="utf-8"))
        links = data.get("links") or {}
        stored_ig = links.get("instagram")
        stored_handle = extract_profile_handle_from_instagram_url(stored_ig) if isinstance(stored_ig, str) else None

        if stored_handle and fh == stored_handle:
            continue

        ok, _reason, strong = passes_relaxed_conservative(
            artist_id=artist_id,
            name=(data.get("name") or "").strip(),
            stored_handle=stored_handle,
            found_handle=fh,
            row=row,
            title=title,
            snippet=snippet,
            min_identity_score=args.min_identity_score,
            min_token_match=args.min_token_match,
        )
        if not ok:
            continue

        if not success_row_extra_gate(
            row,
            artist_id=artist_id,
            name=(data.get("name") or "").strip(),
            found_handle=fh,
            title=title,
            snippet=snippet,
            min_identity_score=args.min_identity_score,
        ):
            continue

        name_s = (data.get("name") or "").strip()
        toks = artist_tokens_for_serp_match(name_s, artist_id)
        stor_id = handle_identity_score(stored_handle or "", artist_id, toks)
        cand_id = handle_identity_score(fh, artist_id, toks)
        junk = is_junk_stored_handle(stored_handle)
        if cand_id < stor_id and not (strong and not junk):
            continue
        if cand_id == stor_id and stor_id > 0 and not junk and not strong:
            continue

        # Junk placeholders (gmail.com, etc.): demand corroboration beyond a random
        # "full name in caption" hit — slug token in Serp *or* high score from log row.
        slug_hits = slug_overlap_in_serp(artist_id, title, snippet)
        log_sc = _log_identity_score(row)
        if junk and slug_hits < 1 and log_sc < 4:
            continue

        url_from_row = extract_profile_handle_from_instagram_url(chosen_url) if chosen_url else None
        if chosen_url and url_from_row == fh:
            url = chosen_url.strip()
            if not url.endswith("/"):
                url = url + "/"
        else:
            url = f"https://www.instagram.com/{fh}/"

        planned.append((artist_id, stored_handle, fh, url, ""))

    print(f"Planned updates: {len(planned)}")
    for aid, old_h, new_h, url, _ in planned:
        print(f"  {aid}: {old_h!r} -> {new_h!r} ({url})")

    if args.dry_run or not planned:
        return

    changed = 0
    for artist_id, _old_h, new_h, url, _ in planned:
        path = data_dir / f"{artist_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        links = data.setdefault("links", {})
        links["instagram"] = url
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed += 1
    print(f"Wrote {changed} artist JSON files.")


if __name__ == "__main__":
    main()
