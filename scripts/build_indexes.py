#!/usr/bin/env python3
"""
Build data/indexes from data/artists/*.json and data/styles/styles.json.
Run from repo root: python scripts/build_indexes.py

Outputs:
  - data/indexes/artists.compact.json  — minimal fields for list + filtering
  - data/indexes/search-index.json     — normalized names for search
  - data/indexes/meta.json             — counts, build timestamp
"""

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTISTS_DIR = REPO_ROOT / "data" / "artists"
STYLES_PATH = REPO_ROOT / "data" / "styles" / "styles.json"
INDEXES_DIR = REPO_ROOT / "data" / "indexes"


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


def build_compact(artists: list[dict]) -> list[dict]:
    """Minimal fields for list + filtering."""
    out = []
    for a in artists:
        tattoos = a.get("tattoos", [])
        first_thumb = tattoos[0]["image_thumb"] if tattoos else None
        out.append({
            "id": a["id"],
            "name": a["name"],
            "location": a["location"],
            "styles": a["styles"],
            "links": {"instagram": a["links"]["instagram"]},
            "tattoo_count": len(tattoos),
            "thumb": first_thumb,
        })
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
        "built_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
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
