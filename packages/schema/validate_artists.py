#!/usr/bin/env python3
"""Validate data/artists/*.json against artist.schema.json. Run from repo root."""
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("pip install jsonschema", file=sys.stderr)
    sys.exit(2)

repo_root = Path(__file__).resolve().parents[2]
schema_path = repo_root / "packages/schema/artist.schema.json"
artists_dir = repo_root / "data/artists"

if not schema_path.exists():
    print("Schema not found", file=sys.stderr)
    sys.exit(1)
with open(schema_path) as f:
    schema = json.load(f)

if not artists_dir.exists():
    sys.exit(0)
errors = []
for p in sorted(artists_dir.glob("*.json")):
    try:
        with open(p) as f:
            data = json.load(f)
        jsonschema.validate(data, schema)
    except (json.JSONDecodeError, jsonschema.ValidationError) as e:
        errors.append(f"{p.name}: {e}")
if errors:
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)
print("OK: artist files valid")
