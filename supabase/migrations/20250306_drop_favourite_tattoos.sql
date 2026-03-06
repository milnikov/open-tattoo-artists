-- Remove favourite_tattoos table (feature removed from MVP)
drop policy if exists "favourite_tattoos_select_own" on public.favourite_tattoos;
drop policy if exists "favourite_tattoos_insert_own" on public.favourite_tattoos;
drop policy if exists "favourite_tattoos_delete_own" on public.favourite_tattoos;
drop table if exists public.favourite_tattoos;
