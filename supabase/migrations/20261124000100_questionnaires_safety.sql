-- Step 3: questionnaire results + safety events.

create type public.questionnaire_instrument as enum ('phq9', 'gad7', 'dass21');

create table public.questionnaire_results (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  instrument  public.questionnaire_instrument not null,
  answers     smallint[] not null check (0 <= all (answers) and 3 >= all (answers)),
  -- {"total": n, "subscales": {"depression": n, ...}} — computed by backend/ai/scoring.py
  score       jsonb not null,
  severity    text not null check (char_length(severity) between 1 and 40),
  level       smallint not null check (level between 0 and 4),
  item9_flag  boolean not null default false,
  created_at  timestamptz not null default now(),
  check (cardinality(answers) = case instrument
                                  when 'phq9' then 9
                                  when 'gad7' then 7
                                  when 'dass21' then 21
                                end)
);

create index questionnaire_results_user_idx
  on public.questionnaire_results (user_id, instrument, created_at desc);

-- Every time the safety rules fire (journal note, PHQ-9 item 9, later chat).
-- The SOS alert service (Week 3) creates counsellor alerts from these rows.
-- Only rule categories are stored, never the student's text.
create type public.safety_source as enum ('journal', 'questionnaire', 'chat', 'sos');

create table public.safety_events (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  source      public.safety_source not null,
  source_id   bigint,
  categories  text[] not null check (cardinality(categories) between 1 and 10),
  created_at  timestamptz not null default now()
);

create index safety_events_user_idx on public.safety_events (user_id, created_at desc);

alter table public.questionnaire_results enable row level security;
alter table public.safety_events enable row level security;

create policy "questionnaire_results: read own"
  on public.questionnaire_results for select to authenticated
  using ((select auth.uid()) = user_id);

-- safety_events: no client access at all (server role only).
