# AI Based Student Mental Health Companionship Application — Project Brief

> Paste this file into a new Claude session (or save it as `CLAUDE.md` in the repo root) and say:
> **"Read PROJECT_BRIEF.md and start with Step 1 of the build plan."**

## 1. What we are building

A mobile/web companion app for college students. The student chats (text, optionally voice and camera), fills standard questionnaires and logs mood and sleep. An AI engine detects emotion and classifies wellbeing risk as **Low / Medium / High**. Low and Medium risk get a supportive reply, coping tips and resources. High risk triggers an **SOS alert** to a college counsellor dashboard. Privacy is a design constraint: **Differential Privacy (DP)** is applied to sensitive features.

This is a final-year academic project (Mangalam College of Engineering, CSE). It is a **supportive screening tool, not a diagnostic or clinical tool**. The report and slides must say so.

Team: Jayakrishnan M G, Jithu James Thomas, Sanjay Sajeev. Timeline: 4 weeks (16 Nov – 11 Dec 2026).

## 2. Tech stack

| Layer | Choice |
| --- | --- |
| Student app | Flutter (Android + web, one codebase) |
| Public website + counsellor/admin portal | Next.js (TypeScript, Tailwind) |
| Backend API | FastAPI (Python 3.11), HTTPS, verifies Supabase JWTs |
| Database | Supabase (Postgres + pgvector), Supabase Auth, Realtime for SOS alerts |
| Chat replies | RAG over a verified knowledge base (pgvector) + Claude API (`claude-opus-5-5`) |
| Background jobs | ARQ + Redis (alerts, document ingestion) |
| Text emotion | DistilBERT / BERT via Hugging Face Transformers, fine-tuned on GoEmotions |
| Face expression | OpenCV + MediaPipe, classifier trained on FER-2013 |
| Voice emotion | librosa (MFCC) + small CNN/MLP, trained on RAVDESS |
| Questionnaires | PHQ-9, GAD-7, DASS-21 scoring |
| Risk classifier | Logistic Regression (scikit-learn) |
| Privacy | Differential Privacy with Opacus (DP-SGD) and/or calibrated noise on features |
| Training | Google Colab (GPU), models exported to `models/` |
| Counsellor dashboard | Next.js portal fed by the same API, live alerts via Supabase Realtime |

Use public or synthetic data only. **Never use real student data during development.**

> **The full design is in `docs/SYSTEM_DESIGN.md` and `docs/SCREENS.md`.** Where they differ from sections 3–12 below (repo layout, schema, API), the design docs win. Key rules: the LLM never decides risk (the classifier + rule overrides do); High-risk replies are fixed templates, not LLM text.

## 3. System architecture

Components and data flow:

1. **Student device (Flutter):** chat interface (text, voice, camera), questionnaires, mood and sleep journal.
2. **Backend API (FastAPI):** authentication, consent and access control, HTTPS. Routes requests to the AI server and the database.
3. **AI server:**
   - Differential Privacy layer (Opacus) sits first.
   - Then three parallel analysers: Text Emotion (DistilBERT/BERT), Facial Expression (OpenCV/MediaPipe), Voice Emotion.
   - Outputs go to **Feature Fusion**, then the **Risk Classifier** (Logistic Regression, Low/Medium/High).
   - Low/Medium goes to the **Response & Recommendation Engine** (reply returns to the student via the API).
   - High goes to the **SOS Alert Service**, which feeds the counsellor dashboard.
   - The risk log is written to the database.
4. **Database:** user profiles, mood and sleep logs, risk and alert logs, resources.
5. **Counsellor / Admin dashboard:** SOS alerts, acknowledgement, aggregated (anonymised) insights.

Workflow in one line: *open app → register/login → provide text / voice / face / questionnaire → privacy layer → AI engine → feature fusion + emotion label → risk classification → (Low/Med) supportive reply, or (High) SOS alert to counsellor; mood & sleep history feeds back into fusion.*

## 4. Data flow (DFD summary)

**Level 0:** one process, "AI Student Mental Health Companionship System", between the external entities **Student** and **Counsellor / Admin**.

**Level 1 processes**

| # | Process | Reads / writes |
| --- | --- | --- |
| 1.0 | Registration & Authentication | writes D1 User Database |
| 2.0 | Multimodal Data Collection | text, voice, face frames, questionnaire answers |
| 3.0 | Privacy Preservation (Differential Privacy) | protected features |
| 4.0 | Emotion Detection & NLP | emotion indicators |
| 5.0 | Wellbeing & Risk Classification | reads D2 trends; writes D3 |
| 6.0 | Chatbot Response & Recommendation | reads D4 resources |
| 7.0 | SOS Alert & Counsellor Dashboard | writes D3 alert log; acknowledgement back |
| 8.0 | Wellness Tracking | writes D2 |

**Data stores:** D1 User Database, D2 Mood / Sleep & Wellness Logs, D3 Alert & Risk Log, D4 Academic Resources & Helplines.

**Level 2 detail:** 3.1 Apply DP noise; 4.1 Text analysis (DistilBERT/BERT); 4.2 Facial expression (OpenCV/MediaPipe); 4.3 Voice/speech analysis; 4.4 Feature fusion; 5.1 Questionnaire scoring (PHQ-9, GAD-7, DASS-21); 5.2 Risk classifier (Logistic Regression); 6.1 Generate personalised response; 7.1 Trigger SOS and notify.

## 5. Suggested repo structure

```
mh-companion/
├── PROJECT_BRIEF.md
├── README.md
├── docker-compose.yml          # postgres + api (+ ai-server later)
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/               # config, security (JWT, hashing)
│   │   ├── db/                 # models.py, session.py, migrations (alembic)
│   │   ├── routers/            # auth, journal, analyze, questionnaire, alerts, resources
│   │   ├── schemas/            # pydantic models
│   │   └── services/           # risk.py, response.py, alerts.py
│   └── tests/
├── ai/                         # model code and training
│   ├── text/                   # fine-tune + inference
│   ├── face/
│   ├── voice/
│   ├── fusion/
│   ├── risk/
│   ├── privacy/                # DP layer, epsilon experiments
│   └── notebooks/              # Colab notebooks
├── models/                     # exported weights (git-ignored, README lists sources)
├── mobile/                     # Flutter app
├── dashboard/                  # counsellor web dashboard
└── docs/                       # report, slides, diagrams
```

## 6. Database schema (starting point)

- `users(id, email, password_hash, role[student|counsellor|admin], consent_given, consent_at, created_at)`
- `mood_logs(id, user_id, mood_score, sleep_hours, note, created_at)`
- `questionnaire_results(id, user_id, instrument[PHQ9|GAD7|DASS21], answers_json, score, severity, created_at)`
- `risk_logs(id, user_id, text_emotion, face_emotion, voice_emotion, fused_vector_json, risk_level[low|medium|high], created_at)`
- `alerts(id, user_id, risk_log_id, status[open|acknowledged|closed], created_at, acknowledged_by, acknowledged_at)`
- `resources(id, title, type[helpline|tip|study], url_or_phone, tags)`

## 7. API (starting contract)

| Method and path | Purpose |
| --- | --- |
| `POST /auth/register`, `POST /auth/login` | Create account (with consent flag), get JWT |
| `POST /journal` / `GET /journal` | Mood and sleep logging and history |
| `POST /questionnaire/{instrument}` | Submit answers, return score and severity |
| `POST /analyze/text` | `{text}` → emotion label and scores |
| `POST /analyze/face` | image frame → expression label |
| `POST /analyze/voice` | audio clip → emotion label |
| `POST /assess` | Fuse available inputs, classify risk, create alert if High, return reply |
| `GET /alerts`, `PATCH /alerts/{id}` | Counsellor dashboard: list and acknowledge |
| `GET /resources` | Helplines, coping tips, study links |

Every endpoint except register/login requires a JWT. Counsellor endpoints require `role=counsellor`.

## 8. Core logic to implement

**Questionnaire severity bands (standard cut-offs)**
- PHQ-9 (0–27): 0–4 minimal, 5–9 mild, 10–14 moderate, 15–19 moderately severe, 20–27 severe. Item 9 (self-harm thoughts) greater than 0 must be flagged for escalation regardless of total.
- GAD-7 (0–21): 0–4 minimal, 5–9 mild, 10–14 moderate, 15–21 severe.
- DASS-21: sum each subscale (depression, anxiety, stress), multiply by 2, then use the published severity bands. Verify the band tables against the official DASS manual before hard-coding.

**Risk classifier:** input is the fused vector (emotion probabilities from each modality, questionnaire scores, recent mood and sleep trend). Output is Low / Medium / High. Optimise for **recall on High**. Report precision, recall, F1 and the confusion matrix. Rule override: any self-harm keyword or PHQ-9 item 9 greater than 0 forces High.

**Missing modalities:** the system must work with text only, so fusion must handle absent face or voice inputs.

**Differential privacy:** apply DP to training (Opacus DP-SGD) and/or add calibrated noise to features before analysis. Run an experiment: accuracy versus epsilon (for example 0.5, 1, 2, 5, 10) and put the plot in the report.

**Response engine:** template and rule-based replies selected by emotion and risk, plus resources from `resources`. Follow safe-messaging practice: no method details, no diagnosis, always offer human help; High risk responses show helpline information and state that a counsellor has been notified.

## 9. Safety, privacy and ethics rules (non-negotiable)

- Explicit consent screen before any camera or microphone use; every modality is optional.
- Raw audio and video frames are processed and discarded, not stored. Store only derived features and labels.
- Passwords are hashed (bcrypt/argon2); HTTPS only; role-based access.
- The counsellor dashboard shows only what is needed for an alert; aggregate insights are anonymised.
- Never present output as a diagnosis. Show a clear "this app does not replace professional help" notice.
- Keep an up-to-date helpline list for the college's region in `resources`; verify numbers before the demo.

## 10. Build plan (4 weeks)

- **Week 1: app skeleton.** Repo, auth, DB schema, consent, mood journal, Flutter login/home screens. *Milestone: login, consent and journal end to end.*
- **Week 2: AI modules.** Text emotion (fine-tune DistilBERT), face expression, voice emotion, questionnaire scoring with unit tests. *Milestone: each module works on sample input via its `/analyze/*` endpoint.*
- **Week 3: fusion, privacy, risk, response.** Fusion, risk classifier, DP layer plus epsilon experiment, response engine, SOS alert, counsellor dashboard. *Milestone: input to risk level to alert, end to end.*
- **Week 4: integration and delivery.** Connect everything, testing (unit, integration, usability with 5–10 peers), results and graphs, update report and slides, demo. *Milestone: final demo and viva.*

Fallback if time slips: use pretrained models for voice and face instead of fine-tuning, and keep the risk classifier simple.

## 11. How Claude should work on this repo

1. Read this file first. Ask before changing the architecture or the tech stack.
2. Work one step at a time, smallest working slice first; run the code and tests before saying something works.
3. Write tests for scoring, risk rules and API endpoints. Keep pure logic (scoring, risk rules) separate from framework code so it is easy to test.
4. Keep secrets in `.env` (never committed); provide `.env.example`.
5. After each step, update `README.md` with how to run it, and list what is done and what is next.
6. Be honest in docs about limitations: public and synthetic training data, not clinical validation.

## 12. Step 1 (start here)

1. Create the repo structure from `docs/SYSTEM_DESIGN.md` §6 with a `README.md`, `.gitignore` and `.env.example`.
2. Set up `supabase/` (Supabase CLI): SQL migrations for `profiles` and `consents`, a trigger that creates a `profiles` row on sign-up, and RLS policies. Add `docker-compose.yml` for the API, worker and Redis.
3. Scaffold the FastAPI app: `/health`, a dependency that verifies the Supabase JWT and loads the role, `GET/PATCH /me`, `POST /me/consents`, with SQLAlchemy models that mirror the Supabase tables.
4. Add pytest tests for valid/expired/missing tokens, role checks and consent recording.
5. Scaffold the Flutter app (`mobile/`) with Supabase login and the consent screen calling the API.
6. Report back what runs and how to start it, then move to the mood journal (`mood_logs`, `POST/GET /journal`).

## 13. Reference datasets and tools

GoEmotions (text), FER-2013 (faces), RAVDESS (speech), Hugging Face Transformers, OpenCV, MediaPipe, librosa, scikit-learn, Opacus (PyTorch differential privacy), FastAPI, Flutter. Check each dataset's licence and terms before use.
