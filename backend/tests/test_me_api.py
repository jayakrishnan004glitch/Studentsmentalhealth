import uuid

from fastapi import Depends, FastAPI

from app.core.deps import require_roles
from app.db.models import UserRole
from tests.conftest import auth_header, make_token


async def test_health_needs_no_auth(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}


async def test_me_requires_token(client) -> None:
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_expired_token(client, create_user) -> None:
    uid = await create_user()
    resp = await client.get("/api/v1/me", headers=auth_header(make_token(uid, expires_in=-60)))
    assert resp.status_code == 401


async def test_valid_token_without_profile_is_forbidden(client) -> None:
    resp = await client.get("/api/v1/me", headers=auth_header(make_token(uuid.uuid4())))
    assert resp.status_code == 403


async def test_new_student_needs_consent(client, create_user) -> None:
    uid = await create_user()
    resp = await client.get("/api/v1/me", headers=auth_header(make_token(uid)))
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["id"] == str(uid)
    assert body["profile"]["role"] == "student"
    assert len(body["profile"]["pseudonym"]) == 8
    assert body["needs_consent"] is True
    assert body["missing_consents"] == ["terms"]
    assert body["consents"] == []
    assert body["current_policy_version"] == "test-v1"


async def test_record_consents_then_revoke(client, create_user) -> None:
    uid = await create_user()
    headers = auth_header(make_token(uid))

    resp = await client.post(
        "/api/v1/me/consents",
        headers=headers,
        json={
            "policy_version": "test-v1",
            "items": [
                {"kind": "terms", "granted": True},
                {"kind": "ai_processing", "granted": True},
                {"kind": "camera", "granted": True},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["needs_consent"] is False
    assert {c["kind"]: c["granted"] for c in body["consents"]} == {
        "terms": True,
        "ai_processing": True,
        "camera": True,
    }

    # Revoking camera later: the latest entry wins, history is kept.
    resp = await client.post(
        "/api/v1/me/consents",
        headers=headers,
        json={"policy_version": "test-v1", "items": [{"kind": "camera", "granted": False}]},
    )
    state = {c["kind"]: c["granted"] for c in resp.json()["consents"]}
    assert state["camera"] is False
    assert state["terms"] is True


async def test_declining_terms_keeps_needs_consent(client, create_user) -> None:
    uid = await create_user()
    resp = await client.post(
        "/api/v1/me/consents",
        headers=auth_header(make_token(uid)),
        json={"policy_version": "test-v1", "items": [{"kind": "terms", "granted": False}]},
    )
    assert resp.status_code == 201
    assert resp.json()["needs_consent"] is True


async def test_outdated_policy_version_conflicts(client, create_user) -> None:
    uid = await create_user()
    resp = await client.post(
        "/api/v1/me/consents",
        headers=auth_header(make_token(uid)),
        json={"policy_version": "old-v0", "items": [{"kind": "terms", "granted": True}]},
    )
    assert resp.status_code == 409


async def test_duplicate_or_unknown_consent_kinds_rejected(client, create_user) -> None:
    uid = await create_user()
    headers = auth_header(make_token(uid))
    dup = {
        "policy_version": "test-v1",
        "items": [{"kind": "terms", "granted": True}, {"kind": "terms", "granted": False}],
    }
    unknown = {"policy_version": "test-v1", "items": [{"kind": "location", "granted": True}]}
    for payload in (dup, unknown):
        resp = await client.post("/api/v1/me/consents", headers=headers, json=payload)
        assert resp.status_code == 422


async def test_update_profile(client, create_user) -> None:
    uid = await create_user()
    resp = await client.patch(
        "/api/v1/me",
        headers=auth_header(make_token(uid)),
        json={"display_name": "  Aru ", "department": "CSE", "year": 3},
    )
    assert resp.status_code == 200
    profile = resp.json()["profile"]
    assert (profile["display_name"], profile["department"], profile["year"]) == ("Aru", "CSE", 3)


async def test_student_cannot_change_role_or_bad_year(client, create_user) -> None:
    uid = await create_user()
    headers = auth_header(make_token(uid))
    for payload in ({"role": "admin"}, {"pseudonym": "X"}, {"year": 9}, {"display_name": ""}):
        resp = await client.patch("/api/v1/me", headers=headers, json=payload)
        assert resp.status_code == 422, payload
    me = await client.get("/api/v1/me", headers=headers)
    assert me.json()["profile"]["role"] == "student"


async def test_require_roles(app, create_user) -> None:
    import httpx

    probe = FastAPI()
    probe.state = app.state  # reuse DB + verifier from the real app

    @probe.get("/counsellor-only")
    async def counsellor_only(user=Depends(require_roles(UserRole.counsellor))):
        return {"role": user.role}

    student = await create_user()
    counsellor = await create_user(role="counsellor")
    transport = httpx.ASGITransport(app=probe)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r1 = await c.get("/counsellor-only", headers=auth_header(make_token(student)))
        r2 = await c.get("/counsellor-only", headers=auth_header(make_token(counsellor)))
    assert r1.status_code == 403
    assert r2.status_code == 200
    assert r2.json() == {"role": "counsellor"}
