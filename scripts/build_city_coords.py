#!/usr/bin/env python3
"""
Build data/indexes/city-coords.json from artist locations and a world cities dataset.
Run from repo root: python scripts/build_city_coords.py

Requires network on first run to download cities.json (cached in data/indexes/cities-source.json).
Output: data/indexes/city-coords.json — "City|Country" -> [lat, lng] for map city-level view.
"""

import json
import re
import unicodedata
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEXES_DIR = REPO_ROOT / "data" / "indexes"
COMPACT_PATH = INDEXES_DIR / "artists.compact.json"
CITIES_SOURCE_URL = "https://raw.githubusercontent.com/lutangar/cities.json/master/cities.json"
CITIES_SOURCE_PATH = INDEXES_DIR / "cities-source.json"
ISO2_URL = "https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/slim-2/slim-2.json"
ISO2_CACHE_PATH = INDEXES_DIR / "country-iso2.json"
OUTPUT_PATH = INDEXES_DIR / "city-coords.json"

# Aliases: artist country name -> ISO2 (when not in official list)
COUNTRY_ALIASES = {
    "United Kingdom": "GB",
    "UK": "GB",
    "United States": "US",
    "USA": "US",
    "South Korea": "KR",
    "Czech Republic": "CZ",
    "Czechia": "CZ",
    "Turkey": "TR",
    "Türkiye": "TR",
    "Netherlands": "NL",
    "Russia": "RU",
    "Vietnam": "VN",
    "DR Congo": "CD",
    "Republic of the Congo": "CG",
    "Congo": "CG",
    "Bolivia": "BO",
    "Iran": "IR",
    "Syria": "SY",
    "Venezuela": "VE",
    "Tanzania": "TZ",
    "Laos": "LA",
    "Brunei": "BN",
    "Moldova": "MD",
    "North Korea": "KP",
    "Palestine": "PS",
    "Taiwan": "TW",
    "Hong Kong": "HK",
    "Macau": "MO",
    "Réunion": "RE",
    "Cape Verde": "CV",
    "Ivory Coast": "CI",
    "North Macedonia": "MK",
    "Unknown": None,
}


def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s.lower().strip())
    return s


def load_country_iso2() -> dict[str, str]:
    """Country name -> ISO2. Load from cache or fetch and cache."""
    if ISO2_CACHE_PATH.exists():
        with open(ISO2_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    try:
        with urllib.request.urlopen(ISO2_URL, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        out = {}
        for row in data:
            name = row.get("name", "")
            if name:
                out[name] = row.get("alpha-2", "")
        out.update(COUNTRY_ALIASES)
        INDEXES_DIR.mkdir(parents=True, exist_ok=True)
        with open(ISO2_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=0)
        return out
    except Exception as e:
        print(f"Warning: could not fetch ISO2 list: {e}. Using aliases only.")
        return dict(COUNTRY_ALIASES)


def load_cities() -> list[dict]:
    """World cities: [{name, lat, lng, country (ISO2)}, ...]."""
    if not CITIES_SOURCE_PATH.exists():
        print("Downloading cities dataset (one-time)...")
        INDEXES_DIR.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(CITIES_SOURCE_URL, timeout=60) as resp:
            raw = resp.read().decode()
        with open(CITIES_SOURCE_PATH, "w", encoding="utf-8") as f:
            f.write(raw)
    with open(CITIES_SOURCE_PATH, encoding="utf-8") as f:
        cities = json.load(f)
    return cities


def get_unique_locations() -> set[tuple[str, str]]:
    """(city, country) from artists.compact.json. Preserve exact strings for key."""
    if not COMPACT_PATH.exists():
        print("Run scripts/build_indexes.py first to create artists.compact.json")
        return set()
    with open(COMPACT_PATH, encoding="utf-8") as f:
        artists = json.load(f)
    out = set()
    for a in artists:
        loc = a.get("location") or {}
        city = (loc.get("city") or "").strip()
        country = (loc.get("country") or "").strip()
        if not country or country == "Unknown":
            continue
        if city:
            out.add((city, country))
    return out


def build_city_coords(
    locations: set[tuple[str, str]],
    cities: list[dict],
    country_iso2: dict[str, str],
) -> dict[str, list[float]]:
    """Build City|Country -> [lat, lng] by matching to cities dataset."""
    # Index cities by (normalized_name, iso2)
    by_key: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for c in cities:
        name = (c.get("name") or "").strip()
        country = (c.get("country") or "").strip().upper()
        if not name or not country or len(country) != 2:
            continue
        lat_s, lng_s = c.get("lat"), c.get("lng")
        try:
            lat, lng = float(lat_s), float(lng_s)
        except (TypeError, ValueError):
            continue
        key = (normalize_name(name), country)
        if key not in by_key:
            by_key[key] = []
        by_key[key].append((lat, lng))

    # Resolve each (city, country) from our data
    coords = {}
    for city, country in locations:
        iso2 = country_iso2.get(country) or country_iso2.get(country.strip())
        if not iso2:
            continue
        key = (normalize_name(city), iso2.upper())
        if key not in by_key:
            continue
        # Prefer first match (or could pick centroid if multiple)
        lat, lng = by_key[key][0]
        coords[f"{city}|{country}"] = [lat, lng]
    return coords


def main() -> None:
    INDEXES_DIR.mkdir(parents=True, exist_ok=True)
    locations = get_unique_locations()
    print(f"Unique city+country from artists: {len(locations)}")
    if not locations:
        return
    country_iso2 = load_country_iso2()
    cities = load_cities()
    print(f"Cities in dataset: {len(cities)}")
    coords = build_city_coords(locations, cities, country_iso2)
    print(f"Resolved coordinates: {len(coords)}")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(coords, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
