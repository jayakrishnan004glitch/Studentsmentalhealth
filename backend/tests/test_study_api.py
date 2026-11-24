import asyncpg

from tests.conftest import auth_header, make_token


async def add_subject(
    raw_db: asyncpg.Connection, scheme: str, code: str, name: str, offerings: list[tuple[str, int]]
) -> int:
    sid = await raw_db.fetchval(
        "insert into public.ktu_subjects (scheme, code, name) values ($1, $2, $3) returning id",
        scheme,
        code,
        name,
    )
    for branch, sem in offerings:
        await raw_db.execute(
            "insert into public.ktu_subject_offerings values ($1, $2, $3)", sid, branch, sem
        )
    return sid


async def add_link(raw_db, sid: int, url: str, *, module=None, active=True, kind="notes") -> int:
    return await raw_db.fetchval(
        "insert into public.study_links (subject_id, module, kind, title, url, active) "
        "values ($1, $2, $3, $4, $5, $6) returning id",
        sid,
        module,
        kind,
        f"Title {url}",
        url,
        active,
    )


async def set_study_profile(client, uid, scheme="2019", branch="CSE", semester=5):
    resp = await client.patch(
        "/api/v1/me",
        headers=auth_header(make_token(uid)),
        json={"ktu_scheme": scheme, "branch": branch, "semester": semester},
    )
    assert resp.status_code == 200, resp.text
    return resp


async def test_catalog_lists_schemes_and_branches(client, create_user) -> None:
    uid = await create_user()
    body = (await client.get("/api/v1/study/catalog", headers=auth_header(make_token(uid)))).json()
    assert [s["code"] for s in body["schemes"]] == ["2024", "2019", "2015"]
    codes = {b["code"] for b in body["branches"]}
    assert {"CSE", "ECE", "ME", "CE", "EEE"} <= codes
    assert body["semesters"] == [1, 2, 3, 4, 5, 6, 7, 8]


async def test_profile_study_fields_validated(client, consented_student) -> None:
    uid = await consented_student()
    headers = auth_header(make_token(uid))
    for payload in (
        {"ktu_scheme": "2099"},
        {"branch": "XYZ"},
        {"semester": 9},
        {"ktu_scheme": "19"},
    ):
        resp = await client.patch("/api/v1/me", headers=headers, json=payload)
        assert resp.status_code == 422, payload

    resp = await set_study_profile(client, uid, branch=" cse ")
    profile = resp.json()["profile"]
    assert (profile["ktu_scheme"], profile["branch"], profile["semester"]) == ("2019", "CSE", 5)


async def test_subjects_need_study_profile(client, consented_student) -> None:
    uid = await consented_student()
    resp = await client.get("/api/v1/study/subjects", headers=auth_header(make_token(uid)))
    assert resp.status_code == 409


async def test_subjects_need_consent(client, create_user) -> None:
    uid = await create_user()
    resp = await client.get("/api/v1/study/subjects", headers=auth_header(make_token(uid)))
    assert resp.status_code == 403


async def test_student_sees_own_semester_subjects(client, consented_student, raw_db) -> None:
    ds = await add_subject(raw_db, "2019", "CST201", "Data Structures", [("CSE", 3)])
    os_ = await add_subject(raw_db, "2019", "CST206", "Operating Systems", [("CSE", 4)])
    common = await add_subject(raw_db, "2019", "MAT101", "Linear Algebra", [("CSE", 1), ("ME", 1)])
    await add_subject(raw_db, "2024", "XYZ301", "Other scheme", [("CSE", 3)])
    await add_link(raw_db, ds, "https://example.org/ds1")
    await add_link(raw_db, ds, "https://example.org/ds2")
    await add_link(raw_db, ds, "https://example.org/hidden", active=False)

    uid = await consented_student()
    await set_study_profile(client, uid, semester=3)
    headers = auth_header(make_token(uid))

    body = (await client.get("/api/v1/study/subjects", headers=headers)).json()
    assert (body["scheme"], body["branch"], body["semester"]) == ("2019", "CSE", 3)
    assert [(s["code"], s["link_count"]) for s in body["subjects"]] == [("CST201", 2)]

    # Browse another semester (e.g. a supplementary exam).
    body = (
        await client.get("/api/v1/study/subjects", headers=headers, params={"semester": 4})
    ).json()
    assert [s["id"] for s in body["subjects"]] == [os_]

    # Common first-year subject appears for ME too.
    body = (
        await client.get(
            "/api/v1/study/subjects", headers=headers, params={"branch": "me", "semester": 1}
        )
    ).json()
    assert [s["id"] for s in body["subjects"]] == [common]


async def test_subject_detail_shows_active_links_in_order(
    client, consented_student, raw_db
) -> None:
    sid = await add_subject(raw_db, "2019", "CST201", "Data Structures", [("CSE", 3)])
    await add_link(raw_db, sid, "https://example.org/m2", module=2)
    await add_link(raw_db, sid, "https://example.org/syl", kind="syllabus")
    await add_link(raw_db, sid, "https://example.org/m1", module=1)
    await add_link(raw_db, sid, "https://example.org/off", module=1, active=False)
    uid = await consented_student()

    resp = await client.get(f"/api/v1/study/subjects/{sid}", headers=auth_header(make_token(uid)))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "CST201"
    assert [(link["module"], link["url"]) for link in body["links"]] == [
        (None, "https://example.org/syl"),
        (1, "https://example.org/m1"),
        (2, "https://example.org/m2"),
    ]

    missing = await client.get(
        "/api/v1/study/subjects/999999", headers=auth_header(make_token(uid))
    )
    assert missing.status_code == 404


async def test_admin_manages_links(client, create_user, consented_student, raw_db) -> None:
    sid = await add_subject(raw_db, "2019", "CST201", "Data Structures", [("CSE", 3)])
    admin = auth_header(make_token(await create_user(role="admin")))
    student = auth_header(make_token(await consented_student()))
    link = {
        "subject_id": sid,
        "module": 1,
        "kind": "notes",
        "title": "Module 1 notes",
        "url": "https://example.org/m1",
        "source_name": "Example",
    }

    assert (await client.post("/api/v1/study/links", headers=student, json=link)).status_code == 403

    resp = await client.post("/api/v1/study/links", headers=admin, json=link)
    assert resp.status_code == 201
    link_id = resp.json()["id"]
    assert resp.json()["active"] is True

    dup = await client.post("/api/v1/study/links", headers=admin, json=link)
    assert dup.status_code == 409

    for bad in (
        {"url": "http://example.org/insecure"},
        {"url": "javascript:alert(1)"},
        {"url": "https://"},
        {"module": 7},
        {"kind": "pdf"},
        {"title": "  "},
    ):
        resp = await client.post("/api/v1/study/links", headers=admin, json={**link, **bad})
        assert resp.status_code == 422, bad

    gone = await client.post(
        "/api/v1/study/links", headers=admin, json={**link, "subject_id": 999999}
    )
    assert gone.status_code == 404

    # Hiding a broken link removes it from the student view.
    resp = await client.patch(
        f"/api/v1/study/links/{link_id}", headers=admin, json={"active": False}
    )
    assert resp.status_code == 200 and resp.json()["active"] is False
    detail = (await client.get(f"/api/v1/study/subjects/{sid}", headers=student)).json()
    assert detail["links"] == []

    assert (await client.delete(f"/api/v1/study/links/{link_id}", headers=admin)).status_code == 204
    assert (await client.delete(f"/api/v1/study/links/{link_id}", headers=admin)).status_code == 404
