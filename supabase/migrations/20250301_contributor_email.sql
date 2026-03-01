-- Add contributor email for display on artist cards (set when user creates contribution)
alter table public.contributions
  add column if not exists contributor_email text;

-- Allow public to read contributions that have an artist (to show "contributed by X" on artist cards)
drop policy if exists "contributions_select_public_contributed" on public.contributions;
create policy "contributions_select_public_contributed"
on public.contributions for select
using (artist_id is not null);
