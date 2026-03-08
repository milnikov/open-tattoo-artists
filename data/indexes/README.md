# Generated indexes — do not edit manually

This folder is populated by CI (`.github/workflows/build-indexes.yml`) or by a local build script.

- `artists.compact.json` — minimal fields for list + filtering
- `search-index.json` — normalized names for quick search
- `countries.json` — allowed country names (full world list from [mledoze/countries](https://github.com/mledoze/countries) + "Unknown"); artists with other values are hidden. Not overwritten by build_indexes; refresh manually if needed.
- `meta.json` — counts, build timestamp, schema version
