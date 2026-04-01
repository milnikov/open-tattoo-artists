#!/usr/bin/env python3
"""
Fetch all tattoo artist profiles from iNKPPL "Find artist" (lazy-loaded list).

The site loads more rows via GET on the same URL as the form action, with:
  X-Requested-With: XMLHttpRequest
  query: type, style, country, city, name (filters), plus onscroll, limit=24, offset=N

Outputs:
  --out-jsonl          one JSON object per line (profile_id, user_slug, profile_url, name)
  --jsonl-missing-only write only rows not in repo / planned handles (same rules as TSV)
  --out-missing-tsv    optional TSV of missing rows (same filter as --jsonl-missing-only)

Usage:
  python discover_inkppl_artists.py --out-jsonl ../inkppl_directory.jsonl --jsonl-missing-only
  python discover_inkppl_artists.py --out-jsonl ../inkppl_directory.jsonl --out-missing-tsv ../inkppl_not_in_repo.tsv
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_root import repo_path

LIST_URL = "https://inkppl.com/en/tattoo-artists/find-tattoo-artist"
BASE_EN = "https://inkppl.com/en/"
LIMIT = 24
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TattooArtistsResearch/1.0; +https://github.com/)",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "text/html,*/*",
}

INKPPL_PATH_RE = re.compile(
    r"https?://(?:www\.)?inkppl\.com/(?:[a-z]{2}/)?(?:user|artist)/([^/?#\s\"']+)",
    re.IGNORECASE,
)


def normalize_slug(raw: str) -> str:
    s = unquote(raw.strip().strip("/"))
    if s.startswith("@"):
        s = s[1:]
    return s.lower()


def fetch_chunk(session: requests.Session, offset: int) -> str:
    params = {
        "type": "",
        "style": "",
        "country": "",
        "city": "",
        "name": "",
        "onscroll": "",
        "limit": LIMIT,
        "offset": offset,
    }
    r = session.get(LIST_URL, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.text


def parse_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select(".rows")
    if not rows:
        return []
    ul = rows[0]
    out: list[dict] = []
    seen: set[tuple[str | None, str]] = set()
    for li in ul.find_all("li", class_=lambda c: c and "master" in c.split()):
        pid = li.get("data-profile-id")
        a = li.select_one('a.profile-link[href^="user/"]') or li.select_one('a[href^="user/"]')
        if not a:
            continue
        href = a.get("href", "").strip()
        if not href.startswith("user/"):
            continue
        slug_raw = href[len("user/") :]
        slug = normalize_slug(slug_raw)
        name_el = li.select_one(".fullNameProfile a")
        name = name_el.get_text(strip=True) if name_el else ""
        key = (pid, slug)
        if key in seen:
            continue
        seen.add(key)
        profile_url = urljoin(BASE_EN, href)
        out.append(
            {
                "profile_id": pid,
                "user_slug": slug,
                "user_slug_raw": slug_raw,
                "profile_url": profile_url,
                "name": name,
            }
        )
    return out


def load_known_slugs_from_artist_json(data_dir: Path) -> set[str]:
    """
    Slugs we already "have" if:
    - any inkppl.com .../user/SLUG or .../artist/SLUG appears in the file (bio, links), or
    - schema "id" (Instagram handle) matches the iNKPPL user slug (common case).
    """
    known: set[str] = set()
    for path in sorted(data_dir.glob("*.json")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in INKPPL_PATH_RE.finditer(text):
            known.add(normalize_slug(m.group(1)))
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            continue
        aid = obj.get("id")
        if isinstance(aid, str) and aid:
            known.add(normalize_slug(aid))
    return known


def load_planned_inkppl_slugs(discovered_path: Path | None) -> set[str]:
    if discovered_path is None or not discovered_path.is_file():
        return set()
    known: set[str] = set()
    try:
        data = json.loads(discovered_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return known
    urls = data.get("artists") or []
    if not isinstance(urls, list):
        return known
    for u in urls:
        if not isinstance(u, str):
            continue
        for m in INKPPL_PATH_RE.finditer(u):
            known.add(normalize_slug(m.group(1)))
    return known


def load_planned_instagram_handles(tsv_path: Path | None) -> set[str]:
    """Tab file with header containing instagram_handle (e.g. off_instagram_links_by_slug.tsv)."""
    if tsv_path is None or not tsv_path.is_file():
        return set()
    out: set[str] = set()
    lines = tsv_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return out
    header = lines[0].split("\t")
    try:
        col = header.index("instagram_handle")
    except ValueError:
        return out
    for line in lines[1:]:
        parts = line.split("\t")
        if col < len(parts) and parts[col]:
            out.add(normalize_slug(parts[col]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Crawl iNKPPL find-artist listing (all lazy-load pages).")
    ap.add_argument("--out-jsonl", type=Path, required=True, help="Write artist rows as JSON lines.")
    ap.add_argument(
        "--jsonl-missing-only",
        action="store_true",
        help="Only write rows whose user_slug is not in data/artists, discovered_pages inkppl URLs, or planned-handles TSV.",
    )
    ap.add_argument(
        "--out-missing-tsv",
        type=Path,
        default=None,
        help="TSV of artists not referenced in repo artist JSON (inkppl slug not found in any file).",
    )
    ap.add_argument(
        "--discovered-json",
        type=Path,
        default=None,
        help="Optional discovered_pages.json; any inkppl URLs here count as 'planned'.",
    )
    ap.add_argument(
        "--planned-handles-tsv",
        type=Path,
        default=None,
        help="TSV with instagram_handle column (treated as planned iNKPPL user slugs when they match).",
    )
    ap.add_argument("--sleep", type=float, default=0.35, help="Seconds between HTTP requests (default 0.35).")
    ap.add_argument("--max-offset", type=int, default=None, help="Stop after this offset (debug).")
    args = ap.parse_args()

    data_dir = repo_path("data", "artists")
    discovered_default = repo_path("packages", "scraper", "discovered_pages.json")
    discovered_path = args.discovered_json if args.discovered_json is not None else discovered_default
    handles_default = repo_path("docs", "off_instagram_links_by_slug.tsv")
    handles_path = args.planned_handles_tsv if args.planned_handles_tsv is not None else handles_default

    known_json = load_known_slugs_from_artist_json(data_dir)
    known_planned = load_planned_inkppl_slugs(discovered_path)
    known_handles = load_planned_instagram_handles(handles_path)
    known_all = known_json | known_planned | known_handles

    session = requests.Session()
    all_by_slug: dict[str, dict] = {}
    offset = 0
    empty_runs = 0

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    while True:
        if args.max_offset is not None and offset > args.max_offset:
            break
        html = fetch_chunk(session, offset)
        chunk = parse_rows(html)
        if not chunk:
            empty_runs += 1
            if empty_runs >= 2:
                break
        else:
            empty_runs = 0

        for row in chunk:
            slug = row["user_slug"]
            if slug not in all_by_slug:
                all_by_slug[slug] = row

        if len(chunk) < LIMIT:
            break
        offset += len(chunk)
        time.sleep(args.sleep)

    ordered = [all_by_slug[s] for s in sorted(all_by_slug)]
    jsonl_rows = [r for r in ordered if r["user_slug"] not in known_all] if args.jsonl_missing_only else ordered
    with args.out_jsonl.open("w", encoding="utf-8") as jf:
        for row in jsonl_rows:
            jf.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Unique artists (by user slug): {len(all_by_slug)}")
    if args.jsonl_missing_only:
        print(f"JSONL rows (missing only): {len(jsonl_rows)}")
    print(f"Written: {args.out_jsonl.resolve()}")

    if args.out_missing_tsv:
        missing = [all_by_slug[s] for s in sorted(all_by_slug) if s not in known_all]
        args.out_missing_tsv.parent.mkdir(parents=True, exist_ok=True)
        with args.out_missing_tsv.open("w", encoding="utf-8") as tf:
            tf.write("profile_id\tuser_slug\tprofile_url\tname\n")
            for row in missing:
                tf.write(
                    f"{row.get('profile_id') or ''}\t{row['user_slug']}\t{row['profile_url']}\t{row.get('name') or ''}\n"
                )
        print(f"Known slugs from data/artists/*.json (inkppl URLs + id): {len(known_json)}")
        print(f"Known inkppl slugs in {discovered_path.name}: {len(known_planned)}")
        print(f"Known instagram_handle from {handles_path.name}: {len(known_handles)}")
        print(f"Missing vs repo+planned (by slug): {len(missing)}")
        print(f"Written: {args.out_missing_tsv.resolve()}")


if __name__ == "__main__":
    main()
