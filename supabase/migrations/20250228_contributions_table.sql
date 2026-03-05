-- Create contributions table (required for "Suggest artist" and profile Contributions)
-- Run this first if you get: relation "public.contributions" does not exist

create table if not exists public.contributions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  type text not null check (type in ('add', 'report')),
  artist_id text,
  github_issue_url text not null,
  status text not null default 'open' check (status in ('open', 'closed', 'merged')),
  contributor_email text,
  created_at timestamptz not null default now()
);

create index if not exists contributions_user_id_idx on public.contributions(user_id);
create index if not exists contributions_artist_id_idx on public.contributions(artist_id);

alter table public.contributions enable row level security;

-- User can see their own contributions
drop policy if exists "contributions_select_own" on public.contributions;
create policy "contributions_select_own"
on public.contributions for select
using (auth.uid() = user_id);

-- User can create their own contributions (e.g. from "Suggest artist")
drop policy if exists "contributions_insert_own" on public.contributions;
create policy "contributions_insert_own"
on public.contributions for insert
with check (auth.uid() = user_id);

-- Public can read contributions that have an artist (for "Contributed by X" on artist cards)
drop policy if exists "contributions_select_public_contributed" on public.contributions;
create policy "contributions_select_public_contributed"
on public.contributions for select
using (artist_id is not null);
