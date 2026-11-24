# MH Companion — AI Student Mental Health Companion

Final-year project (Mangalam College of Engineering, CSE). A **supportive screening tool, not a diagnostic or clinical tool.**

- Design: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) · Screens: [docs/SCREENS.md](docs/SCREENS.md) · Brief: [PROJECT_BRIEF.md](PROJECT_BRIEF.md)

| Folder | What |
| --- | --- |
| `backend/` | FastAPI API (Python 3.11) |
| `mobile/` | Flutter student app (Android + web) |
| `portal/` | Next.js 16 landing page + counsellor/admin portal — Supabase connected, screens in Week 3 |
| `supabase/` | Supabase config + SQL migrations (schema, RLS, triggers) |
| `ml/`, `models/` | Training notebooks and exported weights (Week 2) |
| `data/ktu/` | KTU subjects + study-link CSVs and import instructions |

> ⚠️ **Folder name:** the Flutter web compiler cannot handle a `#` anywhere in the project path. Rename the project folder (e.g. to `mh-companion`) before running `flutter build web` / `flutter run -d chrome`.

## Toolchain (installed 16 Nov 2026)

| Tool | Version | Where |
| --- | --- | --- |
| Python (via uv) | 3.11.18 | `~/.local/share/uv/python` |
| uv | 0.13.8 | `~/.local/bin/uv` |
| Flutter / Dart | 3.50.0 / 3.14.0 | `~/development/flutter` (add `~/development/flutter/bin` to `PATH`) |
| Node / npm | 26.13.0 / 11.20.0 | system |
| Supabase CLI | 3.1.0 | `node_modules` → `npx supabase` |
| Podman | 5.8.7 | system (used instead of Docker) |
| Test DB image | `pgvector/pgvector:pg17` (Postgres 17.12) | podman |

## 1. Supabase

**Option A — Supabase Cloud (recommended for the team):** create a project at supabase.com, then

```bash
npx supabase login
npx supabase link --project-ref <your-project-ref>
npx supabase db push            # applies supabase/migrations
```

**Option B — local:** `npx supabase start` (needs Docker, or Podman with `systemctl --user start podman.socket` and `DOCKER_HOST=unix:///run/user/$UID/podman/podman.sock`). It prints the local URL and keys.

**Supabase Cloud project:** `nuokmxvsasechvwfchrj` (asymmetric ES256 signing keys, so the backend needs no JWT secret). Local env files are already created and git-ignored: `backend/.env`, `mobile/env/dev.json`, `portal/.env.local`.

## 2. Backend

```bash
cd backend
cp .env.example .env                 # fill in DATABASE_URL and SUPABASE_URL
~/.local/bin/uv sync                 # creates .venv with Python 3.11 + dependencies
.venv/bin/uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

### Tests

The tests rebuild the schema from `supabase/migrations` in a throwaway Postgres, so they also test the SQL, trigger and RLS policies.

```bash
podman run -d --name mh-test-db -p 127.0.0.1:54339:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mh_test docker.io/pgvector/pgvector:pg17
# later sessions: podman start mh-test-db

cd backend
.venv/bin/pytest -q        # 137 tests
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Portal (Next.js)

```bash
cd portal
npm install
npm run dev        # http://localhost:3000 — shows "Connected" when Supabase is reachable
```

Supabase helpers live in `portal/src/utils/supabase/` (`server.ts`, `client.ts`); `portal/src/proxy.ts` (Next.js 16's name for middleware) refreshes the session cookie on every request.

## 3. Flutter app

```bash
export PATH="$HOME/development/flutter/bin:$PATH"
cd mobile
cp env/dev.example.json env/dev.json     # fill in Supabase URL + publishable key
flutter pub get
flutter test                              # 21 tests
flutter run -d chrome --dart-define-from-file=env/dev.json     # web
flutter run --dart-define-from-file=env/dev.json               # Android (needs Android SDK)
```

Android emulators reach the backend on the host at `http://10.0.2.2:8000` (the default when `API_BASE_URL` is not set).

## Status

**Step 1 — done**
- Repo structure, `.gitignore`, `.env.example`, `docker-compose.yml` (api, redis, test-db)
- Supabase migration: `profiles`, `consents`, sign-up trigger (always creates a `student`), RLS (students read only their own rows; no client writes)
- FastAPI: `/health`, Supabase JWT verification (JWKS/ES256 and legacy HS256), role dependency, `GET/PATCH /api/v1/me`, `POST /api/v1/me/consents`
- 25 backend tests: tokens (expired, wrong audience/issuer, bad signature, `alg=none`), roles, consent flow, profile validation, trigger, cascade delete, RLS
- Flutter: Supabase sign-in/sign-up, consent screen (terms required; AI, camera, mic, counsellor contact optional), placeholder home, "Get help now" sheet, disclaimer bar; 5 tests

**Step 2 — done: mood & sleep journal**
- Migration `mood_logs` (mood 1–5, optional sleep hours / energy / tags / note), read-own RLS, no client writes, cascade on account delete
- API (consented students only — `403 Consent required` until the terms are accepted):
  - `POST /api/v1/journal` — create an entry
  - `GET /api/v1/journal?limit=&before_id=` — newest first, cursor pagination
  - `GET /api/v1/journal/insights?range=7d|30d|90d&tz_offset_minutes=330` — per-day averages grouped by the student's local day, overall averages, check-in streak, top tags
- Insight maths is pure Python (`app/services/journal.py`) with its own unit tests
- Flutter: quick 5-emoji mood check-in on Home + this week's mood bars and streak (S-01), mood log screen (S-07), journal with 7/30-day mood & sleep charts and recent entries (S-08)
- Tests: backend 42, Flutter 12

**KTU study material — done (links only, all schemes and branches)**
- Migration: `ktu_schemes` (2015/2019/2024), `ktu_branches` (22 B.Tech branches), `ktu_subjects`, `ktu_subject_offerings` (subject ↔ branch + semester, so common subjects appear once), `study_links` (https-only, per module, can be hidden), and `ktu_scheme` / `branch` / `semester` on `profiles`
- API: `GET /api/v1/study/catalog`, `GET /api/v1/study/subjects` (the student's own semester by default; `?semester=` browses others), `GET /api/v1/study/subjects/{id}`; admin-only `POST/PATCH/DELETE /api/v1/study/links`. `PATCH /me` accepts the study profile and rejects unknown codes
- CSV import (all-or-nothing, safe to re-run): fill `data/ktu/subjects.csv` and `links.csv`, then `.venv/bin/python -m scripts.import_study --subjects ../data/ktu/subjects.csv --links ../data/ktu/links.csv` (see [data/ktu/README.md](data/ktu/README.md))
- Flutter: "KTU study material" card on Home → course setup (scheme, branch, semester) → subjects with S1–S8 chips → subject links grouped by module, opened in the browser
- Tests: backend 56, Flutter 17
- **The catalogue is empty until the CSVs are filled in** from the official KTU syllabus

**Step 3 — done: questionnaires + safety rules**
- `backend/ai/scoring.py` — PHQ-9, GAD-7, DASS-21 definitions and scoring (pure Python). DASS-21 subscales ×2 with the manual's bands. **PHQ-9 item 9 > 0 is always flagged**, whatever the total
- `backend/ai/safety.py` — rule-based detection of suicidal / self-harm language (English, Malayalam script, Manglish). Prefers false positives; ignores idioms like "this exam is killing me". Only rule categories are stored, never the text
- `backend/ai/responses.py` — fixed, safe-messaging crisis texts (never LLM-written; they do **not** claim a counsellor was notified yet)
- Migration: `questionnaire_results` (answer count checked per instrument) and `safety_events` (no client access); every safety hit is recorded there for the SOS alert service
- API: `GET /api/v1/questionnaires`, `GET /api/v1/questionnaires/{phq9|gad7|dass21}`, `POST /api/v1/questionnaires/{instrument}`, `GET /api/v1/questionnaires/{instrument}/results`. Submissions and journal entries return `support` (`urgent` or `suggest`)
- Journal notes now go through the safety rules
- Flutter: questionnaire list (S-09), one-question-per-step flow with back button (S-10), result framed as "screening, not a diagnosis" with previous results (S-11), crisis card with **tap-to-call helplines** (S-03) after a flagged note or PHQ-9 item 9
- Tests: backend 137, Flutter 21

**Next — Step 4: SOS + counsellor alerts:** `alerts` table built from `safety_events`, `POST /api/v1/sos` ("Contact counsellor" button), counsellor `GET/PATCH /api/v1/alerts`, audit log, and the portal alerts dashboard with Supabase Realtime. Then update the crisis text to say a counsellor has been notified.

**Known gaps:**
- Android SDK not installed yet (needed for APK builds).
- Helpline numbers in `mobile/lib/core/helplines.dart` must be verified before the demo.
- Safety events are recorded but no counsellor is alerted yet (Step 4). The Malayalam/Manglish safety phrases and the DASS-21 band tables need a review by the team before the demo.
- Charts are a small built-in bar widget; switch to `fl_chart` later if needed.
- No bottom navigation bar yet (Home · Chat · Journal · Resources · Me); added once Chat and Resources exist.
