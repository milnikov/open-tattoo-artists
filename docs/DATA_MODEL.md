# Data model

Artist records are JSON files validated against `packages/schema/artist.schema.json`.

**Visibility:** The app hides artists who only have one image, lack a valid country (see `data/indexes/countries.json`), or have an empty bio; those URLs 404. See PRD (“Visibility: hidden artist cards”).

- **Artist ID** — Instagram handle, lowercase. File: `data/artists/<handle>.json`.  
- **Location** — `city`, `country`; use `"Unknown"` if missing (not empty string).  
- **Styles** — Flat slug list; canonical list: `data/styles/styles.json`.  
- **Tattoos** — `image_id`, `image_full`, `image_thumb`, `analysis` (themes, dominant_colours, body_parts, size_category, confidence_score). Analysis may start empty; URLs may be relative or full CDN.  
- **Other** — `schema_version`, `name`, `links` (source required; instagram, website, etc.), optional `bio`, `tattooing_since`, `updated_at`.

R2 keys: `artists/<handle>/thumb/<id>.webp`, `artists/<handle>/full/<id>.webp`.
