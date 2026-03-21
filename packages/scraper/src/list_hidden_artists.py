#!/usr/bin/env python3
"""
List artist IDs that are hidden on the website (same logic as apps/web/lib/data.ts).
Hidden = tattoo_count <= 1, OR country not in data/indexes/countries.json, OR bio empty.

Run from repo root: python packages/scraper/src/list_hidden_artists.py [--output FILE]
Prints: total artists, visible, hidden, hidden-with-instagram.
With --output: writes hidden artist IDs (one per line or JSON array) for use with enrich --only-ids-file.
With --source-domain HOST: restrict output to artists whose data/artists/<id>.json links.source
uses that host (e.g. tattooswizard.com for TattoosWizard scrapes).
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from _repo_root import repo_path


def get_allowed_countries() -> set[str]:
    p = repo_path("data", "indexes", "countries.json")
    if not p.exists():
        return set()
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return {str(c).strip().lower() for c in data if c}


def source_domain_from_artist_json(artist_id: str) -> str | None:
    """Hostname of links.source from data/artists/<id>.json (lowercase, no www.)."""
    p = repo_path("data", "artists", f"{artist_id}.json")
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        src = (data.get("links") or {}).get("source") or ""
        if not src or not str(src).strip():
            return None
        u = urlparse(str(src).strip())
        h = (u.hostname or "").lower()
        if h.startswith("www."):
            h = h[4:]
        return h or None
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def is_artist_hidden(
    artist: dict,
    allowed_countries: set[str],
) -> bool:
    """Same logic as apps/web/lib/data.ts isArtistHidden()."""
    count = artist.get("tattoo_count") or 0
    if isinstance(artist.get("tattoos"), list):
        count = max(count, len(artist["tattoos"]))
    if count <= 1:
        return True
    country = (artist.get("location") or {}).get("country") or ""
    if not str(country).strip():
        return True
    if str(country).strip().lower() not in allowed_countries:
        return True
    bio = artist.get("bio")
    bio_ok = bio is not None and isinstance(bio, str) and bool(bio.strip())
    if not bio_ok:
        fc = artist.get("follower_count")
        try:
            fc = int(fc) if fc is not None else 0
        except (TypeError, ValueError):
            fc = 0
        if not (count > 5 and fc > 1000):
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description="List hidden artist IDs (website logic).")
    ap.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write hidden artist IDs (with Instagram) to this file. Default: packages/scraper/hidden_artist_ids.json",
    )
    ap.add_argument(
        "--all-hidden",
        action="store_true",
        help="Include all hidden IDs in output; default is only those with Instagram (for enrich).",
    )
    ap.add_argument(
        "--source-domain",
        type=str,
        default=None,
        metavar="HOST",
        help="Only include artists whose links.source host matches (e.g. tattooswizard.com). "
        "Compared case-insensitively; www. is ignored.",
    )
    args = ap.parse_args()

    compact_path = repo_path("data", "indexes", "artists.compact.json")
    if not compact_path.exists():
        print("Run scripts/build_indexes.py first to create data/indexes/artists.compact.json", file=sys.stderr)
        sys.exit(1)

    with open(compact_path, encoding="utf-8") as f:
        artists = json.load(f)
    allowed = get_allowed_countries()

    hidden_ids = []
    hidden_with_ig = []
    for a in artists:
        aid = a.get("id")
        if not aid:
            continue
        if is_artist_hidden(a, allowed):
            hidden_ids.append(aid)
            ig = (a.get("links") or {}).get("instagram") or ""
            if ig and ig.strip():
                hidden_with_ig.append(aid)

    want_domain = None
    if args.source_domain:
        want_domain = str(args.source_domain).strip().lower()
        if want_domain.startswith("www."):
            want_domain = want_domain[4:]

    def filter_by_source(ids: list[str]) -> list[str]:
        if not want_domain:
            return ids
        out = []
        for aid in ids:
            dom = source_domain_from_artist_json(aid)
            if dom == want_domain:
                out.append(aid)
        return out

    total = len(artists)
    visible = total - len(hidden_ids)
    print(f"Total artists: {total}")
    print(f"Visible (shown on site): {visible}")
    print(f"Hidden: {len(hidden_ids)}")
    print(f"Hidden with Instagram: {len(hidden_with_ig)}")

    ids_to_write = hidden_ids if args.all_hidden else hidden_with_ig
    if want_domain:
        ids_to_write = filter_by_source(ids_to_write)
        label = "hidden (all)" if args.all_hidden else "hidden with Instagram"
        print(f"{label} with links.source host == {want_domain!r}: {len(ids_to_write)}")

    out_path = args.output
    if out_path is None:
        out_path = str(repo_path("packages", "scraper", "hidden_artist_ids.json"))
    if ids_to_write and out_path:
        p = Path(out_path)
        if not p.is_absolute():
            p = repo_path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(ids_to_write, f, indent=2)
        print(f"Wrote {len(ids_to_write)} IDs to {p}")


if __name__ == "__main__":
    main()
