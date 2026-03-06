# Data model

Artist records are JSON files validated against `packages/schema/artist.schema.json`. Key points:

- **Artist ID** = Instagram handle (lowercase). One file per artist: `data/artists/<handle>.json`.
- **Location**: `city` and `country`; use `"Unknown"` when not known (never empty string).
- **Styles**: Flat list of slugs. Canonical list: `data/styles/styles.json`.
- **Tattoos**: Array of objects with `image_id`, `image_full`, `image_thumb`, and `analysis` (themes, dominant_colours, body_parts, size_category, confidence_score). Analysis may be empty initially; image URLs may be relative or full CDN.
- **Other fields**: `schema_version`, `name`, `links` (source required; instagram, website, etc. optional), optional `bio`, `tattooing_since`, `updated_at`.

R2 image keys follow `artists/<handle>/thumb/<id>.webp` and `artists/<handle>/full/<id>.webp`.
