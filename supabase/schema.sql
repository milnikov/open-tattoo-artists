-- Open Tattoo Artists — Supabase schema (MVP)
-- Assumes Supabase Auth is enabled (auth.users)

-- 1) Profiles (optional but nice)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now()
);

-- 2) Favourites - artists (private)
create table if not exists public.favourites (
  user_id uuid not null references auth.users(id) on delete cascade,
  artist_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, artist_id)
);

create index if not exists favourites_user_id_idx on public.favourites(user_id);
create index if not exists favourites_artist_id_idx on public.favourites(artist_id);

-- 2b) Favourite tattoos (artist_id + tattoo_id)
create table if not exists public.favourite_tattoos (
  user_id uuid not null references auth.users(id) on delete cascade,
  artist_id text not null,
  tattoo_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, artist_id, tattoo_id)
);

create index if not exists favourite_tattoos_user_id_idx on public.favourite_tattoos(user_id);

-- 3) Contributions (tracks GitHub Issues created from the site)
create table if not exists public.contributions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  type text not null check (type in ('add', 'report')),
  artist_id text,
  github_issue_url text not null,
  status text not null default 'open' check (status in ('open', 'closed', 'merged')),
  created_at timestamptz not null default now()
);

create index if not exists contributions_user_id_idx on public.contributions(user_id);
create index if not exists contributions_artist_id_idx on public.contributions(artist_id);

-- ========== RLS ==========
alter table public.profiles enable row level security;
alter table public.favourites enable row level security;
alter table public.favourite_tattoos enable row level security;
alter table public.contributions enable row level security;

-- Profiles: user can read/update their own profile
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles for select
using (auth.uid() = id);

drop policy if exists "profiles_upsert_own" on public.profiles;
create policy "profiles_upsert_own"
on public.profiles for insert
with check (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
on public.profiles for update
using (auth.uid() = id);

-- Favourites: user can CRUD only their own favourites
drop policy if exists "favourites_select_own" on public.favourites;
create policy "favourites_select_own"
on public.favourites for select
using (auth.uid() = user_id);

drop policy if exists "favourites_insert_own" on public.favourites;
create policy "favourites_insert_own"
on public.favourites for insert
with check (auth.uid() = user_id);

drop policy if exists "favourites_delete_own" on public.favourites;
create policy "favourites_delete_own"
on public.favourites for delete
using (auth.uid() = user_id);

-- Favourite tattoos: user can CRUD only their own
drop policy if exists "favourite_tattoos_select_own" on public.favourite_tattoos;
create policy "favourite_tattoos_select_own"
on public.favourite_tattoos for select using (auth.uid() = user_id);
drop policy if exists "favourite_tattoos_insert_own" on public.favourite_tattoos;
create policy "favourite_tattoos_insert_own"
on public.favourite_tattoos for insert with check (auth.uid() = user_id);
drop policy if exists "favourite_tattoos_delete_own" on public.favourite_tattoos;
create policy "favourite_tattoos_delete_own"
on public.favourite_tattoos for delete using (auth.uid() = user_id);

-- Contributions: user can see & create their own contributions
drop policy if exists "contributions_select_own" on public.contributions;
create policy "contributions_select_own"
on public.contributions for select
using (auth.uid() = user_id);

drop policy if exists "contributions_insert_own" on public.contributions;
create policy "contributions_insert_own"
on public.contributions for insert
with check (auth.uid() = user_id);

-- Optional: allow user to update nothing (status managed by maintainer / automation)
-- If you want users to edit their own contribution record, add an UPDATE policy.
