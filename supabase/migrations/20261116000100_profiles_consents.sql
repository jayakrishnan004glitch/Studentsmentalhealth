-- Step 1: profiles + consents, sign-up trigger, row-level security.
-- All writes go through the FastAPI backend (server role, bypasses RLS).
-- Clients may only READ their own rows directly; RLS is defence in depth.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------- types
create type public.user_role as enum ('student', 'counsellor', 'admin');

create type public.consent_kind as enum (
  'terms',              -- required to use the app
  'ai_processing',      -- required for chat (text is sent to the LLM provider)
  'camera',             -- optional face check-in
  'microphone',         -- optional voice check-in
  'counsellor_contact'  -- optional: counsellor may see contact details on an alert
);

-- ---------------------------------------------------------------- profiles
create table public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  role         public.user_role not null default 'student',
  display_name text check (char_length(display_name) between 1 and 50),
  department   text check (char_length(department) between 1 and 80),
  year         smallint check (year between 1 and 6),
  -- shown to counsellors instead of the student's name
  pseudonym    text not null unique
               default upper(substr(encode(gen_random_bytes(5), 'hex'), 1, 8)),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

comment on table public.profiles is
  'One row per auth user. role is never taken from client input.';

create function public.set_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Create a profile automatically when someone signs up through Supabase Auth.
-- Always 'student'; counsellors/admins are promoted by an admin.
create function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id) values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------- consents
-- Append-only log: the current state of a consent is its latest row.
create table public.consents (
  id             bigint generated always as identity primary key,
  user_id        uuid not null references public.profiles (id) on delete cascade,
  kind           public.consent_kind not null,
  granted        boolean not null,
  policy_version text not null check (char_length(policy_version) between 1 and 32),
  created_at     timestamptz not null default now()
);

create index consents_user_kind_latest_idx
  on public.consents (user_id, kind, created_at desc, id desc);

-- ---------------------------------------------------------------- RLS
alter table public.profiles enable row level security;
alter table public.consents enable row level security;

create policy "profiles: read own"
  on public.profiles for select to authenticated
  using ((select auth.uid()) = id);

create policy "consents: read own"
  on public.consents for select to authenticated
  using ((select auth.uid()) = user_id);

-- No insert/update/delete policies on purpose: clients cannot change
-- their role, pseudonym or consent history directly.
