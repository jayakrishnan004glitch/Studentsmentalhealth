from datetime import UTC, datetime, timedelta

from tests.conftest import auth_header, make_token

URL = "/api/v1/journal"


async def test_journal_requires_token(client) -> None:
    assert (await client.get(URL)).status_code == 401
    assert (await client.post(URL, json={"mood_score": 3})).status_code == 401


async def test_journal_requires_consent(client, create_user) -> None:
    uid = await create_user()  # has not accepted the terms
    resp = await client.post(URL, headers=auth_header(make_token(uid)), json={"mood_score": 3})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Consent required"


async def test_journal_is_students_only(client, create_user, raw_db, settings) -> None:
    uid = await create_user(role="counsellor")
    await raw_db.execute(
        "insert into public.consents (user_id, kind, granted, policy_version) "
        "values ($1, 'terms', true, $2)",
        uid,
        settings.current_policy_version,
    )
    resp = await client.get(URL, headers=auth_header(make_token(uid)))
    assert resp.status_code == 403


async def test_create_entry(client, consented_student) -> None:
    uid = await consented_student()
    resp = await client.post(
        URL,
        headers=auth_header(make_token(uid)),
        json={
            "mood_score": 2,
            "sleep_hours": 6.25,
            "energy": 3,
            "tags": ["exams", "sleep", "exams"],
            "note": "  Big test tomorrow  ",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mood_score"] == 2
    assert body["sleep_hours"] == 6.2  # rounded to one decimal (banker's rounding)
    assert body["energy"] == 3
    assert body["tags"] == ["exams", "sleep"]
    assert body["note"] == "Big test tomorrow"
    assert body["created_at"]


async def test_minimal_entry_and_blank_note(client, consented_student) -> None:
    uid = await consented_student()
    resp = await client.post(
        URL, headers=auth_header(make_token(uid)), json={"mood_score": 5, "note": "   "}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert (body["sleep_hours"], body["energy"], body["tags"], body["note"]) == (
        None,
        None,
        [],
        None,
    )


async def test_invalid_entries_rejected(client, consented_student) -> None:
    uid = await consented_student()
    headers = auth_header(make_token(uid))
    for payload in (
        {},
        {"mood_score": 0},
        {"mood_score": 6},
        {"mood_score": 3, "sleep_hours": 25},
        {"mood_score": 3, "sleep_hours": -1},
        {"mood_score": 3, "energy": 9},
        {"mood_score": 3, "tags": ["not-a-tag"]},
        {"mood_score": 3, "note": "x" * 1001},
        {"mood_score": 3, "user_id": "someone-else"},
    ):
        resp = await client.post(URL, headers=headers, json=payload)
        assert resp.status_code == 422, payload


async def test_list_is_own_newest_first_and_paginated(client, consented_student) -> None:
    me, other = await consented_student(), await consented_student()
    headers = auth_header(make_token(me))
    for mood in (1, 2, 3, 4, 5):
        await client.post(URL, headers=headers, json={"mood_score": mood})
    await client.post(URL, headers=auth_header(make_token(other)), json={"mood_score": 1})

    page1 = (await client.get(URL, headers=headers, params={"limit": 3})).json()
    assert [i["mood_score"] for i in page1["items"]] == [5, 4, 3]
    assert page1["next_before_id"] is not None

    page2 = (
        await client.get(
            URL, headers=headers, params={"limit": 3, "before_id": page1["next_before_id"]}
        )
    ).json()
    assert [i["mood_score"] for i in page2["items"]] == [2, 1]
    assert page2["next_before_id"] is None


async def test_insights_by_local_day(client, consented_student, raw_db) -> None:
    uid = await consented_student()
    now = datetime.now(UTC)

    async def insert(at: datetime, mood: int, sleep: float | None, tags: list[str]) -> None:
        await raw_db.execute(
            "insert into public.mood_logs (user_id, mood_score, sleep_hours, tags, created_at) "
            "values ($1, $2, $3, $4, $5)",
            uid,
            mood,
            sleep,
            tags,
            at,
        )

    await insert(now, 4, 7.0, ["exams"])
    await insert(now - timedelta(minutes=1), 2, None, ["exams", "family"])
    await insert(now - timedelta(days=1), 3, 5.0, [])
    await insert(now - timedelta(days=40), 1, 4.0, ["money"])  # outside 30d

    resp = await client.get(
        f"{URL}/insights",
        headers=auth_header(make_token(uid)),
        params={"range": "30d", "tz_offset_minutes": 330},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["range_days"] == 30
    assert len(body["days"]) == 30
    assert body["entries"] == 3
    assert body["mood_avg"] == 3.0
    assert body["sleep_avg"] == 6.0
    assert body["streak_days"] == 2
    assert body["top_tags"][0] == {"tag": "exams", "count": 2}
    assert "money" not in {t["tag"] for t in body["top_tags"]}
    today = body["days"][-1]
    assert today["entries"] == 2 and today["mood_avg"] == 3.0 and today["sleep_avg"] == 7.0


async def test_insights_validates_params(client, consented_student) -> None:
    uid = await consented_student()
    headers = auth_header(make_token(uid))
    for params in ({"range": "1y"}, {"tz_offset_minutes": 2000}):
        resp = await client.get(f"{URL}/insights", headers=headers, params=params)
        assert resp.status_code == 422, params
    empty = (await client.get(f"{URL}/insights", headers=headers)).json()
    assert (empty["range_days"], empty["entries"], empty["streak_days"]) == (7, 0, 0)


async def test_note_with_crisis_language_returns_urgent_support(
    client, consented_student, raw_db
) -> None:
    uid = await consented_student()
    headers = auth_header(make_token(uid))
    resp = await client.post(
        URL, headers=headers, json={"mood_score": 1, "note": "I don't want to live anymore"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["support"]["level"] == "urgent"
    assert body["note"] == "I don't want to live anymore"  # still saved for the student

    event = await raw_db.fetchrow(
        "select source, source_id, categories from public.safety_events where user_id = $1", uid
    )
    assert (event["source"], event["source_id"], list(event["categories"])) == (
        "journal",
        body["id"],
        ["suicidal_ideation"],
    )

    calm = await client.post(URL, headers=headers, json={"mood_score": 2, "note": "exams :("})
    assert calm.json()["support"] is None
    assert (
        await raw_db.fetchval("select count(*) from public.safety_events where user_id = $1", uid)
        == 1
    )
