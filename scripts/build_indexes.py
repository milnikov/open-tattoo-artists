#!/usr/bin/env python3
"""
Build data/indexes from data/artists/*.json and data/styles/styles.json.
Run from repo root: python scripts/build_indexes.py

Outputs:
  - data/indexes/artists.compact.json  — minimal fields for list + filtering
  - data/indexes/search-index.json     — normalized names for search
  - data/indexes/meta.json             — counts, build timestamp

Note: countries.json is a full world list (see data/indexes/README.md); not overwritten by this script.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTISTS_DIR = REPO_ROOT / "data" / "artists"
STYLES_PATH = REPO_ROOT / "data" / "styles" / "styles.json"
JUNK_STYLES_PATH = REPO_ROOT / "data" / "styles" / "junk_styles.json"
INDEXES_DIR = REPO_ROOT / "data" / "indexes"


def _load_junk_styles() -> frozenset[str]:
    """Same tokens as validate_styles_locations — keeps browse/map style lists clean."""
    if not JUNK_STYLES_PATH.is_file():
        return frozenset()
    try:
        data = json.loads(JUNK_STYLES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return frozenset()
    if not isinstance(data, list):
        return frozenset()
    return frozenset(str(x) for x in data)


JUNK_STYLES = _load_junk_styles()


def source_domain_from_url(url) -> str | None:
    """Hostname from links.source, lowercase, no leading www."""
    if url is None:
        return None
    s = str(url).strip()
    if not s:
        return None
    try:
        u = urlparse(s)
        h = (u.hostname or "").lower()
        if h.startswith("www."):
            h = h[4:]
        return h or None
    except (TypeError, ValueError):
        return None


def normalize_for_search(name: str) -> str:
    """Lowercase, strip, normalize unicode, collapse whitespace."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name.lower().strip())
    s = re.sub(r"\s+", " ", s)
    return s


def load_artists() -> list[dict]:
    """Load all artist JSON files."""
    artists = []
    if not ARTISTS_DIR.exists():
        return artists
    for p in sorted(ARTISTS_DIR.glob("*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                artists.append(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: skip {p.name}: {e}")
    return artists


def _normalize_handle(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    if not v:
        return None
    if v.startswith("http://") or v.startswith("https://"):
        parsed = urlparse(v)
        path = (parsed.path or "").strip("/")
        if not path:
            return None
        v = path.split("/")[0]
    return v or None


def _build_follow_graph(artists: list[dict]) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, int]]:
    """
    Build in-db follow graph from instagram_enriched.following handles.
    Returns:
      - followers_by_target: target_id -> [follower_artist_id]
      - following_by_source: source_id -> [target_artist_id]
      - followed_count: target_id -> number of follower artists
    """
    handle_to_id: dict[str, str] = {}
    for a in artists:
        aid = a.get("id")
        if not isinstance(aid, str) or not aid:
            continue
        handle_to_id[aid.lower()] = aid
        links = a.get("links") or {}
        ig_link_handle = _normalize_handle((links or {}).get("instagram"))
        if ig_link_handle:
            handle_to_id.setdefault(ig_link_handle, aid)

    followers_by_target: dict[str, list[str]] = {}
    following_by_source: dict[str, list[str]] = {}
    followed_count: dict[str, int] = {}

    for a in artists:
        src_id = a.get("id")
        if not isinstance(src_id, str) or not src_id:
            continue
        ie = a.get("instagram_enriched") or {}
        following = ie.get("following") if isinstance(ie, dict) else None
        if not isinstance(following, list):
            continue

        seen_targets: set[str] = set()
        for raw in following:
            handle = _normalize_handle(raw)
            if not handle:
                continue
            target_id = handle_to_id.get(handle)
            if not target_id or target_id == src_id:
                continue
            if target_id in seen_targets:
                continue
            seen_targets.add(target_id)
            following_by_source.setdefault(src_id, []).append(target_id)
            followers_by_target.setdefault(target_id, []).append(src_id)
            followed_count[target_id] = followed_count.get(target_id, 0) + 1

    return followers_by_target, following_by_source, followed_count


def build_compact(artists: list[dict]) -> list[dict]:
    """Minimal fields for list + filtering. Up to 8 thumbs for list view (mobile strip)."""
    followers_by_target, following_by_source, followed_count = _build_follow_graph(artists)
    out = []
    for a in artists:
        tattoos = a.get("tattoos", [])
        thumbs = [t["image_thumb"] for t in tattoos[:8]]
        first_thumb = thumbs[0] if thumbs else None
        raw_styles = a.get("styles")
        if isinstance(raw_styles, list):
            styles_clean = [s for s in raw_styles if s not in JUNK_STYLES]
        else:
            styles_clean = []
        entry = {
            "id": a["id"],
            "name": a["name"],
            "location": a["location"],
            "styles": styles_clean,
            "links": {"instagram": a["links"]["instagram"]},
            "tattoo_count": len(tattoos),
            "thumb": first_thumb,
            "thumbs": thumbs,
        }
        if a.get("bio"):
            entry["bio"] = a["bio"]
        if a.get("updated_at"):
            entry["updated_at"] = a["updated_at"]
        ie = a.get("instagram_enriched") or {}
        fc = ie.get("follower_count")
        if fc is not None and isinstance(fc, (int, float)):
            entry["follower_count"] = int(fc)
        ppu = ie.get("profile_pic_url")
        if isinstance(ppu, str) and ppu.strip():
            entry["instagram_profile_pic"] = ppu.strip()
        links = a.get("links") or {}
        sd = source_domain_from_url(links.get("source"))
        if sd:
            entry["source_domain"] = sd
        v = a.get("verified")
        if v in ("artist", "studio", "need_to_check"):
            entry["verified"] = v
        if a.get("instagram_enriched"):
            entry["instagram_enriched"] = True
        aid = a.get("id")
        if isinstance(aid, str) and aid:
            entry["followed_by_artists_count"] = int(followed_count.get(aid, 0))
            entry["followers_in_db"] = followers_by_target.get(aid, [])
            entry["following_in_db"] = following_by_source.get(aid, [])
        out.append(entry)
    return sorted(out, key=lambda x: x["name"].lower())


def build_search_index(artists: list[dict]) -> list[dict]:
    """Normalized names for quick search."""
    out = []
    for a in artists:
        norm = normalize_for_search(a["name"])
        if norm:
            out.append({"id": a["id"], "name": a["name"], "normalized": norm})
    return sorted(out, key=lambda x: x["normalized"])


def build_meta(artists: list[dict]) -> dict:
    """Counts, build timestamp, schema version."""
    styles_path = STYLES_PATH
    styles_count = 0
    if styles_path.exists():
        try:
            with open(styles_path, encoding="utf-8") as f:
                styles_data = json.load(f)
                styles_count = len(styles_data) if isinstance(styles_data, list) else 0
        except Exception:
            pass
    return {
        "artist_count": len(artists),
        "schema_version": 2,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "styles_count": styles_count,
    }


def main():
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    artists = load_artists()

    compact = build_compact(artists)
    with open(INDEXES_DIR / "artists.compact.json", "w", encoding="utf-8") as f:
        json.dump(compact, f, indent=2, ensure_ascii=False)

    search_idx = build_search_index(artists)
    with open(INDEXES_DIR / "search-index.json", "w", encoding="utf-8") as f:
        json.dump(search_idx, f, indent=2, ensure_ascii=False)

    meta = build_meta(artists)
    with open(INDEXES_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"Built indexes: {len(artists)} artists")


if __name__ == "__main__":
    main()
