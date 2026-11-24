"""Checks the SQL migrations directly: sign-up trigger and row-level security."""

import uuid

import asyncpg
import pytest


async def test_signup_trigger_creates_student_profile(raw_db, create_user) -> None:
    uid = await create_user()
    row = await raw_db.fetchrow("select role, pseudonym from public.profiles where id = $1", uid)
    assert row["role"] == "student"
    assert len(row["pseudonym"]) == 8


async def test_deleting_auth_user_cascades(raw_db, create_user) -> None:
    uid = await create_user()
    await raw_db.execute(
        "insert into public.consents (user_id, kind, granted, policy_version) "
        "values ($1, 'terms', true, 'v1')",
        uid,
    )
    await raw_db.execute("delete from auth.users where id = $1", uid)
    profiles = await raw_db.fetchval("select count(*) from public.profiles where id = $1", uid)
    consents = await raw_db.fetchval("select count(*) from public.consents where user_id = $1", uid)
    assert (profiles, consents) == (0, 0)


async def _as_authenticated(conn: asyncpg.Connection, uid: uuid.UUID) -> None:
    await conn.execute("set local role authenticated")
    await conn.execute("select set_config('request.jwt.claim.sub', $1, true)", str(uid))


async def test_rls_students_see_only_their_own_profile(raw_db, create_user) -> None:
    me, other = await create_user(), await create_user()
    async with raw_db.transaction():
        await _as_authenticated(raw_db, me)
        ids = {r["id"] for r in await raw_db.fetch("select id from public.profiles")}
    assert ids == {me}
    assert other not in ids


async def test_rls_blocks_client_writes(raw_db, create_user) -> None:
    me = await create_user()
    # Updating own role directly (bypassing the API) must have no effect.
    async with raw_db.transaction():
        await _as_authenticated(raw_db, me)
        result = await raw_db.execute("update public.profiles set role = 'admin' where id = $1", me)
    assert result == "UPDATE 0"
    assert await raw_db.fetchval("select role from public.profiles where id = $1", me) == "student"

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with raw_db.transaction():
            await _as_authenticated(raw_db, me)
            await raw_db.execute(
                "insert into public.consents (user_id, kind, granted, policy_version) "
                "values ($1, 'terms', true, 'v1')",
                me,
            )


async def test_rls_mood_logs_read_own_no_writes(raw_db, create_user) -> None:
    me, other = await create_user(), await create_user()
    for uid in (me, other):
        await raw_db.execute(
            "insert into public.mood_logs (user_id, mood_score) values ($1, 3)", uid
        )
    async with raw_db.transaction():
        await _as_authenticated(raw_db, me)
        owners = {r["user_id"] for r in await raw_db.fetch("select user_id from public.mood_logs")}
        deleted = await raw_db.execute("delete from public.mood_logs")
    assert owners == {me}
    assert deleted == "DELETE 0"

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with raw_db.transaction():
            await _as_authenticated(raw_db, me)
            await raw_db.execute(
                "insert into public.mood_logs (user_id, mood_score) values ($1, 3)", me
            )


async def test_mood_logs_constraints_and_cascade(raw_db, create_user) -> None:
    uid = await create_user()
    for bad in ("mood_score) values ($1, 6", "mood_score, sleep_hours) values ($1, 3, 30"):
        with pytest.raises(asyncpg.CheckViolationError):
            await raw_db.execute(f"insert into public.mood_logs (user_id, {bad})", uid)
    await raw_db.execute("insert into public.mood_logs (user_id, mood_score) values ($1, 3)", uid)
    await raw_db.execute("delete from auth.users where id = $1", uid)
    count = await raw_db.fetchval("select count(*) from public.mood_logs where user_id = $1", uid)
    assert count == 0


async def test_rls_study_links_read_active_only_no_writes(raw_db, create_user) -> None:
    me = await create_user()
    sid = await raw_db.fetchval(
        "insert into public.ktu_subjects (scheme, code, name) "
        "values ('2019', 'CST201', 'Data Structures') returning id"
    )
    await raw_db.execute(
        "insert into public.study_links (subject_id, kind, title, url, active) values "
        "($1, 'notes', 'On', 'https://example.org/on', true), "
        "($1, 'notes', 'Off', 'https://example.org/off', false)",
        sid,
    )
    async with raw_db.transaction():
        await _as_authenticated(raw_db, me)
        titles = [r["title"] for r in await raw_db.fetch("select title from public.study_links")]
        branches = await raw_db.fetchval("select count(*) from public.ktu_branches")
    assert titles == ["On"]
    assert branches > 0

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with raw_db.transaction():
            await _as_authenticated(raw_db, me)
            await raw_db.execute(
                "insert into public.study_links (subject_id, kind, title, url) "
                "values ($1, 'notes', 'X', 'https://example.org/x')",
                sid,
            )

    with pytest.raises(asyncpg.CheckViolationError):
        await raw_db.execute(
            "insert into public.study_links (subject_id, kind, title, url) "
            "values ($1, 'notes', 'X', 'http://insecure.example')",
            sid,
        )


async def test_rls_questionnaires_own_and_safety_events_hidden(raw_db, create_user) -> None:
    me, other = await create_user(), await create_user()
    for uid in (me, other):
        await raw_db.execute(
            "insert into public.questionnaire_results "
            "(user_id, instrument, answers, score, severity, level) "
            "values ($1, 'gad7', '{0,0,0,0,0,0,0}', '{}', 'minimal', 0)",
            uid,
        )
        await raw_db.execute(
            "insert into public.safety_events (user_id, source, categories) "
            "values ($1, 'journal', '{suicidal_ideation}')",
            uid,
        )
    async with raw_db.transaction():
        await _as_authenticated(raw_db, me)
        owners = {
            r["user_id"]
            for r in await raw_db.fetch("select user_id from public.questionnaire_results")
        }
        events = await raw_db.fetchval("select count(*) from public.safety_events")
    assert owners == {me}
    assert events == 0  # students cannot read safety events at all


async def test_questionnaire_answer_count_must_match_instrument(raw_db, create_user) -> None:
    uid = await create_user()
    with pytest.raises(asyncpg.CheckViolationError):
        await raw_db.execute(
            "insert into public.questionnaire_results "
            "(user_id, instrument, answers, score, severity, level) "
            "values ($1, 'phq9', '{0,0,0,0,0,0,0}', '{}', 'minimal', 0)",
            uid,
        )
    with pytest.raises(asyncpg.CheckViolationError):
        await raw_db.execute(
            "insert into public.questionnaire_results "
            "(user_id, instrument, answers, score, severity, level) "
            "values ($1, 'gad7', '{0,0,0,0,0,0,4}', '{}', 'minimal', 0)",
            uid,
        )
