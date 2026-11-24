# KTU subjects and study links

The app shows each student the subjects for **their own scheme, branch and semester**, and for each subject a list of **links to external sites** (notes, previous question papers, syllabus, videos). No files are hosted by the app.

Fill in the two CSV files here, then import them (see the bottom of this file). You can edit them in Excel or Google Sheets. Save as **CSV UTF-8**.

## `subjects.csv`

| Column | Example | Rules |
| --- | --- | --- |
| `scheme` | `2019` | `2015`, `2019` or `2024` |
| `code` | `CST201` | Subject code from the KTU syllabus (letters and digits) |
| `name` | `Data Structures` | Subject name |
| `semester` | `3` | 1–8 |
| `branches` | `CSE;IT` | Branch codes separated by `;`, or `ALL` for every branch (first-year common subjects) |

If branches take the same subject in **different semesters**, add one row per semester (same code). Electives: one row per elective, in the semester they are offered.

**Branch codes:** CSE, ECE, EEE, ME, CE, IT, AEI, CHE, BT, BME, AU, MR, RA, AD (AI & Data Science), AIML, CY (Cyber Security), AR, FT, PE, SF, PO, MT. To add a branch, add a new migration in `supabase/migrations/` with `insert into public.ktu_branches (code, name) values (...) on conflict do nothing;`.

## `links.csv`

| Column | Example | Rules |
| --- | --- | --- |
| `scheme` | `2019` | Must match a subject |
| `subject_code` | `CST201` | Must match a subject in that scheme |
| `module` | `1` | 1–6, or **blank** for the whole subject |
| `kind` | `notes` | `notes`, `question_paper`, `syllabus`, `video`, `textbook`, `other` |
| `title` | `Module 1 – Arrays and Linked Lists` | Shown to students |
| `url` | `https://...` | Must start with `https://` |
| `source_name` | `KTU official` | Optional: shown next to the link, so students know where it goes |

## Content rules

- **Link, don't copy.** Only link to pages. Never download another site's PDFs and re-host them.
- Prefer official and openly licensed sources: the KTU website (syllabus, question papers), NPTEL / SWAYAM courses, faculty pages, and openly shared class notes (with the author's permission).
- Check that every link opens before importing. Broken links can be hidden later by an admin (`PATCH /api/v1/study/links/{id}` with `{"active": false}`).

## Import

From `backend/`:

```bash
# validate only
.venv/bin/python -m scripts.import_study --subjects ../data/ktu/subjects.csv --links ../data/ktu/links.csv --dry-run
# import (uses DATABASE_URL from backend/.env)
.venv/bin/python -m scripts.import_study --subjects ../data/ktu/subjects.csv --links ../data/ktu/links.csv
```

The import is all-or-nothing: if any row has a problem, nothing is written and every problem is listed with its line number. Running it again with updated files is safe: subjects and links are updated, not duplicated.
