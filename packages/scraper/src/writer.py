"""
Write data/artists/<handle>.json conforming to artist.schema.json (schema_version 2).
"""

from datetime import date
from typing import Optional
from pathlib import Path

from _repo_root import repo_path


def empty_analysis():
    """Schema-compliant empty analysis object."""
    return {
        "themes": [],
        "dominant_colours": [],
        "body_parts": [],
        "size_category": None,
        "confidence_score": None,
    }


def build_artist_json(
    handle: str,
    name: str,
    city: str,
    country: str,
    styles: list[str],
    instagram_url: str,
    website: Optional[str],
    source_url: str,
    tattoos: list[dict],
) -> dict:
    """
    Build artist dict for schema v2.
    tattoos: list of {"image_id", "image_full", "image_thumb"}
    """
    links = {"instagram": instagram_url, "source": source_url}
    if website:
        links["website"] = website

    tattoo_objs = []
    for t in tattoos:
        tattoo_objs.append({
            "image_id": t["image_id"],
            "image_full": t["image_full"],
            "image_thumb": t["image_thumb"],
            "analysis": empty_analysis(),
        })

    return {
        "schema_version": 2,
        "id": handle,
        "name": name,
        "location": {"city": city, "country": country},
        "styles": styles,
        "links": links,
        "tattoos": tattoo_objs,
        "updated_at": date.today().isoformat(),
    }


def write_artist(handle: str, data: dict) -> Path:
    """Write artist JSON to data/artists/<handle>.json."""
    out_dir = repo_path("data", "artists")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{handle}.json"
    import json
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out_path
