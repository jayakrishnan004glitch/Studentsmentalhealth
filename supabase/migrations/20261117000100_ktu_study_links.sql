-- KTU study materials: a catalogue of subjects per scheme / branch / semester,
-- each with curated LINKS to external sites (notes, question papers, syllabus,
-- videos). No files are hosted. Links are added by admins (API or CSV import).

-- ---------------------------------------------------------------- lookups
create table public.ktu_schemes (
  code text primary key check (code ~ '^[0-9]{4}$'),
  name text not null check (char_length(name) between 1 and 80)
);

insert into public.ktu_schemes (code, name) values
  ('2015', '2015 scheme'),
  ('2019', '2019 scheme'),
  ('2024', '2024 scheme');

create table public.ktu_branches (
  code text primary key check (code ~ '^[A-Z]{2,5}$'),
  name text not null check (char_length(name) between 1 and 120)
);

-- B.Tech branches. Add more with another migration (insert ... on conflict do nothing).
insert into public.ktu_branches (code, name) values
  ('CSE', 'Computer Science and Engineering'),
  ('ECE', 'Electronics and Communication Engineering'),
  ('EEE', 'Electrical and Electronics Engineering'),
  ('ME',  'Mechanical Engineering'),
  ('CE',  'Civil Engineering'),
  ('IT',  'Information Technology'),
  ('AEI', 'Applied Electronics and Instrumentation Engineering'),
  ('CHE', 'Chemical Engineering'),
  ('BT',  'Biotechnology'),
  ('BME', 'Biomedical Engineering'),
  ('AU',  'Automobile Engineering'),
  ('MR',  'Mechatronics Engineering'),
  ('RA',  'Robotics and Automation'),
  ('AD',  'Artificial Intelligence and Data Science'),
  ('AIML','Artificial Intelligence and Machine Learning'),
  ('CY',  'Computer Science and Engineering (Cyber Security)'),
  ('AR',  'Aeronautical Engineering'),
  ('FT',  'Food Technology'),
  ('PE',  'Production Engineering'),
  ('SF',  'Safety and Fire Engineering'),
  ('PO',  'Polymer Engineering'),
  ('MT',  'Metallurgical and Materials Engineering')
on conflict do nothing;

-- ---------------------------------------------------------------- subjects
create table public.ktu_subjects (
  id     bigint generated always as identity primary key,
  scheme text not null references public.ktu_schemes (code),
  code   text not null check (code ~ '^[A-Z0-9]{2,20}$'),
  name   text not null check (char_length(name) between 1 and 200),
  unique (scheme, code)
);

-- Which branches take a subject in which semester (common first-year subjects
-- and shared electives appear once in ktu_subjects, many times here).
create table public.ktu_subject_offerings (
  subject_id bigint   not null references public.ktu_subjects (id) on delete cascade,
  branch     text     not null references public.ktu_branches (code),
  semester   smallint not null check (semester between 1 and 8),
  primary key (subject_id, branch, semester)
);

create index ktu_subject_offerings_lookup_idx
  on public.ktu_subject_offerings (branch, semester);

-- ---------------------------------------------------------------- links
create type public.study_link_kind as enum (
  'notes', 'question_paper', 'syllabus', 'video', 'textbook', 'other'
);

create table public.study_links (
  id          bigint generated always as identity primary key,
  subject_id  bigint not null references public.ktu_subjects (id) on delete cascade,
  module      smallint check (module between 1 and 6),   -- null = whole subject
  kind        public.study_link_kind not null,
  title       text not null check (char_length(title) between 1 and 200),
  url         text not null check (url ~ '^https://' and char_length(url) <= 2048),
  source_name text check (char_length(source_name) between 1 and 80),
  active      boolean not null default true,   -- hide broken links without deleting
  created_by  uuid references public.profiles (id) on delete set null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (subject_id, url)
);

create index study_links_subject_idx on public.study_links (subject_id) where active;

create trigger study_links_set_updated_at
  before update on public.study_links
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------- profiles
-- What the student studies; drives which subjects they see after login.
alter table public.profiles
  add column ktu_scheme text references public.ktu_schemes (code),
  add column branch     text references public.ktu_branches (code),
  add column semester   smallint check (semester between 1 and 8);

-- ---------------------------------------------------------------- RLS
-- Catalogue data is not personal: any signed-in user may read it.
-- Writes go through the API (admin only) or the import script.
alter table public.ktu_schemes enable row level security;
alter table public.ktu_branches enable row level security;
alter table public.ktu_subjects enable row level security;
alter table public.ktu_subject_offerings enable row level security;
alter table public.study_links enable row level security;

create policy "ktu_schemes: read" on public.ktu_schemes
  for select to authenticated using (true);
create policy "ktu_branches: read" on public.ktu_branches
  for select to authenticated using (true);
create policy "ktu_subjects: read" on public.ktu_subjects
  for select to authenticated using (true);
create policy "ktu_subject_offerings: read" on public.ktu_subject_offerings
  for select to authenticated using (true);
create policy "study_links: read active" on public.study_links
  for select to authenticated using (active);
