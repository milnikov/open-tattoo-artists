# Schema package

This package contains JSON Schemas used to validate open metadata in `data/`.

## Files
- `artist.schema.json` — main artist file schema (schema_version = 2)
- `styles.schema.json` — canonical styles list
- `index.schema.json` — generated index files (optional validation)

## How to validate (example)
Use AJV (Node) or `jsonschema` (Python) in CI to validate every `data/artists/*.json` file.

Notes:
- Artist IDs are Instagram handles, lowercased.
- Tattoo analysis fields are present but may be empty in MVP.
