# Open Tattoo Artists

## Product Requirements Document (Final)

**Version:** 1.0\
**Date:** 2026-02-28\
**Status:** MVP + AI-Ready Architecture

------------------------------------------------------------------------

# 1. Overview

**Product Name:** Open Tattoo Artists\
**Type:** Open-source tattoo artist directory\
**Positioning:** Open-source library of tattoo artists and tattoo works

Open Tattoo Artists is a transparent, community-maintained, open-source
tattoo directory where:

-   GitHub is the canonical source of truth
-   Metadata is versioned and publicly auditable
-   Images are stored in Cloudflare R2
-   Users can contribute via GitHub Issues
-   Tattoos are first-class structured objects
-   AI enrichment is supported but optional

------------------------------------------------------------------------

# 2. Core Principles

1.  GitHub is the permanent canonical metadata source.
2.  The project is an open library, not a marketplace.
3.  Submissions and corrections flow through GitHub Issues.
4.  No artist duplication (Instagram handle is unique ID).
5.  Tattoos are individual entities and can be favourited.
6.  AI enrichment must never overwrite human canonical data.

------------------------------------------------------------------------

# 3. Product Phases

## Phase 1 --- MVP

### Features

-   Google Authentication (Supabase)
-   Artist directory list
-   Filters:
    -   Location (free text)
    -   Style (flat list)
-   Search by name
-   Default sorting: alphabetical
-   Artist page:
    -   Name
    -   Location
    -   Styles
    -   Instagram link
    -   Website (optional)
    -   Source link
    -   Image gallery (\~50 images max)
    -   Add artist to favourites
    -   Report problem
-   Profile page:
    -   Favourite artists
    -   Contributions + status

### Visibility: hidden artist cards

Some artist cards are **not shown** in the directory (list, search, filters) and their profile page returns 404. This keeps the catalogue focused on entries with usable info. An artist is hidden if **any** of the following is true:

-   **Only one image** — artist has at most one tattoo image (insufficient for meaningful browsing).
-   **Wrong or missing country** — `location.country` is empty or not in the allowed list. The allowed list is `data/indexes/countries.json` (full world list + "Unknown"); values like provinces, regions, or placeholders (e.g. "N/A") are not allowed.
-   **Empty about** — `bio` is missing or only whitespace.

Artists that meet all criteria (more than one image, allowed country, non-empty bio) are shown. Direct links to hidden artists (e.g. `/artists/<id>`) respond with 404. See `data/indexes/README.md` for index build notes and `apps/web/lib/data.ts` for the implementation.

### Non-Goals (MVP)

-   No map view
-   No badges
-   No artist claim
-   No monetization
-   No multilingual support

### Post-MVP (planned)

See **docs/POST_MVP_PLAN.md** for two planned updates: (1) artist ranking by “followed by other artists” with a toggle between alphabetical and this view, and (2) OpenClaw bot setup to automatically process GitHub issues.

------------------------------------------------------------------------

# 4. Data Architecture

## 4.1 GitHub Repository Structure

/data\
/artists\
/`<artist-id>`{=html}.json\
/styles\
styles.json\
/indexes\
artists.compact.json\
search-index.json

GitHub Actions: - Validate JSON schema - Rebuild indexes - Trigger
Vercel deployment

------------------------------------------------------------------------

## 4.2 Artist Schema (Canonical)

``` json
{
  "id": "instagram-handle",
  "name": "Artist Name",
  "location": {
    "city": "Porto",
    "country": "Portugal"
  },
  "styles": ["blackwork", "dotwork"],
  "links": {
    "instagram": "https://instagram.com/handle",
    "website": "https://...",
    "source": "https://..."
  },
  "tattoos": [
    {
      "image_id": "001",
      "image_full": "artists/handle/full/001.webp",
      "image_thumb": "artists/handle/thumb/001.webp",
      "analysis": {
        "themes": [],
        "dominant_colours": [],
        "body_parts": [],
        "size_category": null,
        "confidence_score": null
      }
    }
  ],
  "updated_at": "YYYY-MM-DD"
}
```

Rules:

-   `id` = Instagram handle (unique, global)
-   No duplicate artists allowed
-   `image_id` must be stable and never reused
-   `image_full` and `image_thumb` may be relative paths (e.g. `artists/handle/full/001.webp`) or full CDN URLs
-   `analysis` may be empty initially; AI phase may add `model_version`
-   Human-edited metadata lives only in GitHub

------------------------------------------------------------------------

# 5. Image Storage (Cloudflare R2)

Structure:

artists/`<instagram-handle>`{=html}/\
thumb/`<image>`{=html}.webp\
full/`<image>`{=html}.webp

Constraints:

-   Max \~50 images per artist (MVP)
-   WEBP format
-   Target \~200KB average
-   Served via CDN
-   Long cache TTL

Estimated scale:

50k artists × 50 images ≈ 2.5M images\
\~500GB storage

------------------------------------------------------------------------

# 6. Supabase (User + Enrichment Layer)

## Tables

### profiles

-   id
-   email
-   name
-   avatar_url
-   created_at

### favourites (artist favourites)

-   user_id
-   artist_id
-   created_at

### contributions

-   user_id
-   type (add/report)
-   github_issue_url
-   status
-   created_at

### tattoo_analysis (AI Layer)

-   tattoo_id
-   artist_id
-   themes (array)
-   dominant_colours (array)
-   body_parts (array)
-   size_category
-   confidence_score
-   model_version
-   updated_at

Supabase AI layer is optional and may sync back to GitHub if approved.

------------------------------------------------------------------------

# 7. Computer Vision Architecture (Future Phase)

### Goals

-   Automatically analyze tattoo images
-   Extract structured tags
-   Enable advanced filtering

### Processing Flow

1.  Image stored in Cloudflare R2
2.  Background worker processes batches
3.  AI extracts:
    -   Theme detection
    -   Colour clustering
    -   Body placement detection
    -   Estimated size category
4.  Results stored in Supabase (AI layer)

AI results must include confidence_score and model_version.

------------------------------------------------------------------------

# 8. Search Roadmap

## Phase 1

-   Filter by location
-   Filter by style
-   Search by name

## Phase 2

-   Filter by theme
-   Filter by dominant colour
-   Filter by body part
-   Combined filters

## Phase 3

-   Visual similarity search
-   AI recommendations
-   Similar tattoos
-   Similar artists

------------------------------------------------------------------------

# 9. Performance Requirements

-   Directory load \< 2 seconds
-   Thumbnails only in list view
-   Lazy load full images
-   Static index for MVP search
-   CDN caching enabled

------------------------------------------------------------------------

# 10. Risks & Mitigation

### Content ownership complaints

-   Users can report problems via GitHub Issue (report-problem); maintainers handle case-by-case

### AI tagging errors

-   Confidence score required
-   Sampling validation
-   No automatic overwrite of canonical data

### Scaling beyond 50k artists

-   Move search to indexed backend
-   Introduce tag indexing in Supabase

------------------------------------------------------------------------

# 11. Success Metrics

MVP: - % users saving ≥1 favourite - Artist page views/session - Weekly
new contributions - % issues resolved within 7 days

Post-AI: - % tattoos analyzed - Advanced filter usage rate - Combined
filter sessions - AI tag accuracy sampling

------------------------------------------------------------------------

# 12. Definition of Done (MVP)

-   Google auth working
-   Directory list + filters functional
-   Artist page functional
-   Images served from R2
-   Artist favourites working
-   GitHub Issue submission working
-   Contribute tab visible
-   Production deployment stable

------------------------------------------------------------------------

# 13. Strategic Positioning

Open Tattoo Artists is:

-   An open-source cultural archive
-   A structured visual dataset
-   A foundation for future AI-powered tattoo search
-   A transparent alternative to closed directories

GitHub remains the permanent canonical library.

------------------------------------------------------------------------

End of Document
