# Moderation

Submissions flow only through GitHub Issues. Templates: **add-artist** (Suggest artist) and **report-problem** (Report problem), under `.github/ISSUE_TEMPLATE/`.

- **Review**: Maintainers triage issues, then scrape/update metadata and commit to `data/artists/` and optionally upload images to R2.
- **Accepted**: Valid artist with Instagram handle; no duplicates (artist ID = handle). Report-problem issues are handled case-by-case (corrections, takedowns, etc.).
- **Rejected**: Duplicate artist, missing required data, or spam. Close with a short comment.
