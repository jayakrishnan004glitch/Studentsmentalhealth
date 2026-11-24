-- Step 2: mood & sleep journal (screens S-07 log, S-08 history & insights).
-- Writes go through the FastAPI backend; clients may only read their own rows.

create table public.mood_logs (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  mood_score  smallint not null check (mood_score between 1 and 5),
  -- Optional: a student may log mood several times a day but sleep once.
  sleep_hours numeric(3, 1) check (sleep_hours between 0 and 24),
  energy      smallint check (energy between 1 and 5),
  -- Vocabulary (exams, family, ...) is validated by the API so it can grow
  -- without a migration.
  tags        text[] not null default '{}' check (cardinality(tags) <= 10),
  note        text check (char_length(note) between 1 and 1000),
  created_at  timestamptz not null default now()
);

comment on table public.mood_logs is
  'Mood and sleep journal. Feeds the mood/sleep trend used by risk fusion.';

create index mood_logs_user_created_idx
  on public.mood_logs (user_id, created_at desc, id desc);

alter table public.mood_logs enable row level security;

create policy "mood_logs: read own"
  on public.mood_logs for select to authenticated
  using ((select auth.uid()) = user_id);

-- No insert/update/delete policies on purpose (writes go through the API).
