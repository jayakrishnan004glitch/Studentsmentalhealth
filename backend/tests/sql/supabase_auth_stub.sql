-- Minimal stand-in for the parts of Supabase's `auth` schema that our
-- migrations depend on, so migrations can be tested on plain Postgres.
-- Never apply this to a real Supabase project.

create schema if not exists auth;

create table if not exists auth.users (
  id    uuid primary key default gen_random_uuid(),
  email text
);

create or replace function auth.uid() returns uuid
language sql stable as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

do $$
begin
  create role anon nologin;
exception when duplicate_object then null;
end $$;

do $$
begin
  create role authenticated nologin;
exception when duplicate_object then null;
end $$;

grant usage on schema public, auth to anon, authenticated;
