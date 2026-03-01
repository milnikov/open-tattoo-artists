# Supabase

This project uses Supabase for:
- Google-only authentication
- Private favourites
- Tracking user contributions (GitHub Issue URLs)

## Apply schema
1. Run `schema.sql` in Supabase SQL Editor.
2. Run migrations in `migrations/` (e.g. `20250301_contributor_email.sql`) if present.

## Marking a contribution as merged
When you add an artist from a user’s “Suggest artist” issue, update the contribution so the user sees the artist card in their Contributions tab and “Contributed by” appears on the artist:

```sql
update public.contributions
set artist_id = 'the-artist-id',  -- e.g. from data/artists/<id>.json
    status = 'merged'
where github_issue_url = 'https://github.com/owner/repo/issues/123';
```

## Notes
- RLS is enabled for all user data tables.
- Catalogue metadata is not stored in Supabase (lives in GitHub).
