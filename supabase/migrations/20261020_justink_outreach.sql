-- Private JustInk outreach tracker. Access is limited to m.milnikov@gmail.com via RLS.

create table if not exists public.justink_outreach (
  artist_id text primary key,
  status text
    check (
      status is null
      or status = any (
        array[
          'reached',
          'no_reply',
          'interested',
          'not_interested',
          'scheduled',
          'got_feedback',
          'became_a_user'
        ]::text[]
      )
    ),
  comment text not null default '',
  updated_at timestamptz not null default now(),
  constraint justink_outreach_comment_len check (char_length(comment) <= 4000)
);

create index if not exists justink_outreach_status_idx
  on public.justink_outreach (status);

create index if not exists justink_outreach_updated_at_idx
  on public.justink_outreach (updated_at desc);

comment on table public.justink_outreach is
  'Private JustInk outreach tracker for m.milnikov@gmail.com.';

alter table public.justink_outreach enable row level security;

revoke all on table public.justink_outreach from anon;
revoke all on table public.justink_outreach from public;
grant select, insert, update, delete on table public.justink_outreach to authenticated;

drop policy if exists justink_outreach_admin_select on public.justink_outreach;
create policy justink_outreach_admin_select
on public.justink_outreach
for select
to authenticated
using ((auth.jwt() ->> 'email') = 'm.milnikov@gmail.com');

drop policy if exists justink_outreach_admin_insert on public.justink_outreach;
create policy justink_outreach_admin_insert
on public.justink_outreach
for insert
to authenticated
with check ((auth.jwt() ->> 'email') = 'm.milnikov@gmail.com');

drop policy if exists justink_outreach_admin_update on public.justink_outreach;
create policy justink_outreach_admin_update
on public.justink_outreach
for update
to authenticated
using ((auth.jwt() ->> 'email') = 'm.milnikov@gmail.com')
with check ((auth.jwt() ->> 'email') = 'm.milnikov@gmail.com');

drop policy if exists justink_outreach_admin_delete on public.justink_outreach;
create policy justink_outreach_admin_delete
on public.justink_outreach
for delete
to authenticated
using ((auth.jwt() ->> 'email') = 'm.milnikov@gmail.com');
