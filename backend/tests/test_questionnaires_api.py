from tests.conftest import auth_header, make_token

URL = "/api/v1/questionnaires"


async def test_requires_consent(client, create_user) -> None:
    uid = await create_user()
    assert (await client.get(URL, headers=auth_header(make_token(uid)))).status_code == 403


async def test_list_and_definitions(client, consented_student) -> None:
    headers = auth_header(make_token(await consented_student()))
    body = (await client.get(URL, headers=headers)).json()
    assert [q["instrument"] for q in body] == ["phq9", "gad7", "dass21"]
    assert [q["item_count"] for q in body] == [9, 7, 21]
    assert all(q["last_taken_at"] is None for q in body)

    phq = (await client.get(f"{URL}/phq9", headers=headers)).json()
    assert len(phq["items"]) == 9 and len(phq["options"]) == 4
    assert (await client.get(f"{URL}/bdi", headers=headers)).status_code == 422


async def test_submit_phq9_scores_and_stores(client, consented_student, raw_db) -> None:
    uid = await consented_student()
    headers = auth_header(make_token(uid))
    resp = await client.post(f"{URL}/phq9", headers=headers, json={"answers": [1] * 8 + [0]})
    assert resp.status_code == 201
    body = resp.json()
    assert (body["total"], body["severity"], body["item9_flag"]) == (8, "mild", False)
    assert body["support"] is None

    row = await raw_db.fetchrow(
        "select answers, severity, level from public.questionnaire_results where id = $1",
        body["id"],
    )
    assert list(row["answers"]) == [1] * 8 + [0]
    assert (row["severity"], row["level"]) == ("mild", 1)
    events = await raw_db.fetchval(
        "select count(*) from public.safety_events where user_id=$1", uid
    )
    assert events == 0

    listed = (await client.get(URL, headers=headers)).json()[0]
    assert listed["last_taken_at"] is not None
    assert listed["last_severity_label"] == "Mild"


async def test_item9_forces_urgent_support_and_safety_event(
    client, consented_student, raw_db
) -> None:
    uid = await consented_student()
    resp = await client.post(
        f"{URL}/phq9", headers=auth_header(make_token(uid)), json={"answers": [0] * 8 + [1]}
    )
    body = resp.json()
    assert body["severity"] == "minimal"
    assert body["item9_flag"] is True
    assert body["support"]["level"] == "urgent"
    # Must not promise a counsellor alert before the alert service exists.
    assert "notified" not in body["support"]["message"].lower()

    event = await raw_db.fetchrow(
        "select source, source_id, categories from public.safety_events where user_id = $1", uid
    )
    assert (event["source"], event["source_id"], list(event["categories"])) == (
        "questionnaire",
        body["id"],
        ["phq9_item9"],
    )


async def test_high_band_suggests_support(client, consented_student) -> None:
    headers = auth_header(make_token(await consented_student()))
    body = (await client.post(f"{URL}/gad7", headers=headers, json={"answers": [3] * 7})).json()
    assert body["severity"] == "severe"
    assert body["support"]["level"] == "suggest"


async def test_dass21_returns_subscales(client, consented_student) -> None:
    headers = auth_header(make_token(await consented_student()))
    body = (await client.post(f"{URL}/dass21", headers=headers, json={"answers": [1] * 21})).json()
    assert {s["code"]: s["score"] for s in body["subscales"]} == {
        "depression": 14,
        "anxiety": 14,
        "stress": 14,
    }
    assert body["max_total"] == 126


async def test_invalid_answers_rejected(client, consented_student, raw_db) -> None:
    uid = await consented_student()
    headers = auth_header(make_token(uid))
    for inst, payload in (
        ("phq9", {"answers": [0] * 8}),
        ("gad7", {"answers": [0] * 6 + [4]}),
        ("dass21", {"answers": []}),
        ("phq9", {"answers": [0] * 9, "user_id": "x"}),
        ("phq9", {}),
    ):
        resp = await client.post(f"{URL}/{inst}", headers=headers, json=payload)
        assert resp.status_code == 422, (inst, payload)
    count = await raw_db.fetchval(
        "select count(*) from public.questionnaire_results where user_id = $1", uid
    )
    assert count == 0


async def test_history_is_own_and_newest_first(client, consented_student) -> None:
    me, other = await consented_student(), await consented_student()
    headers = auth_header(make_token(me))
    for total in (0, 5, 10):
        answers = [min(3, max(0, total - 3 * i)) for i in range(7)]
        await client.post(f"{URL}/gad7", headers=headers, json={"answers": answers})
    await client.post(
        f"{URL}/gad7", headers=auth_header(make_token(other)), json={"answers": [3] * 7}
    )
    hist = (await client.get(f"{URL}/gad7/results", headers=headers)).json()
    assert [h["total"] for h in hist] == [10, 5, 0]
    assert [h["severity"] for h in hist] == ["moderate", "mild", "minimal"]
    assert (await client.get(f"{URL}/phq9/results", headers=headers)).json() == []
