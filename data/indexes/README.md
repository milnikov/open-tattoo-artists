# Generated indexes — do not edit manually

This folder is populated by CI (`.github/workflows/build-indexes.yml`) or by a local build script.

- `artists.compact.json` — minimal fields for list + filtering
- `search-index.json` — normalized names for quick search
- `countries.json` — allowed country names (full world list from [mledoze/countries](https://github.com/mledoze/countries) + "Unknown"); artists with other values are hidden. Not overwritten by build_indexes; refresh manually if needed.
- `meta.json` — counts, build timestamp, schema version
- `country-centroids.json` — country name → [lat, lng] for map (generated from REST Countries or similar)
- `city-coords.json` — `"City|Country"` → [lat, lng] for city-level map; run `python scripts/build_city_coords.py` to generate
- `cities-source.json` — cached world cities dataset (downloaded by build_city_coords.py; can be gitignored)
- `country-iso2.json` — cached country name → ISO2 (optional; built by build_city_coords.py)
