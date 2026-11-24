"""Test setup.

Requires a throwaway Postgres (with pgvector) reachable at TEST_DATABASE_URL.
Quick start with podman or docker:

    podman run -d --name mh-test-db -p 127.0.0.1:54339:5432 \
      -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=mh_test pgvector/pgvector:pg17

The schema is rebuilt from supabase/migrations at the start of the session,
so these tests also verify the SQL migrations, trigger and RLS policies.
"""

import os
import time
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import httpx
import jwt
import pytest

from app.core.config import Settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "supabase" / "migrations"
AUTH_STUB = Path(__file__).parent / "sql" / "supabase_auth_stub.sql"

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:54339/mh_test"
)
RAW_DSN = TEST_DATABASE_URL.replace("+asyncpg", "")
JWT_SECRET = "test-secret-at-least-32-bytes-long-0123456789"
SUPABASE_URL = "http://supabase.test"
ISSUER = f"{SUPABASE_URL}/auth/v1"

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL,
        supabase_url=SUPABASE_URL,
        supabase_jwt_secret=JWT_SECRET,
        current_policy_version="test-v1",
    )


@pytest.fixture(scope="session")
async def raw_db() -> AsyncIterator[asyncpg.Connection]:
    try:
        conn = await asyncpg.connect(RAW_DSN, timeout=5)
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.exit(f"Test database not reachable at {RAW_DSN}: {exc}", returncode=2)
    await conn.execute(
        """
        drop schema if exists public cascade;
        drop schema if exists auth cascade;
        create schema public;
        grant all on schema public to postgres, public;
        """
    )
    await conn.execute(AUTH_STUB.read_text())
    await conn.execute(
        """
        alter default privileges in schema public
          grant all on tables to anon, authenticated;
        alter default privileges in schema public
          grant all on sequences to anon, authenticated;
        """
    )
    for migration in sorted(MIGRATIONS.glob("*.sql")):
        await conn.execute(migration.read_text())
    yield conn
    await conn.close()


@pytest.fixture(autouse=True)
async def clean_db(raw_db: asyncpg.Connection) -> None:
    await raw_db.execute("truncate auth.users, public.ktu_subjects restart identity cascade")


@pytest.fixture(scope="session")
async def app(settings: Settings, raw_db: asyncpg.Connection):
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def make_token(
    sub: uuid.UUID | str,
    *,
    expires_in: int = 3600,
    audience: str = "authenticated",
    issuer: str = ISSUER,
    secret: str = JWT_SECRET,
) -> str:
    now = int(time.time())
    payload = {
        "sub": str(sub),
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + expires_in,
        "email": "student@example.edu",
        "role": "authenticated",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_user(raw_db: asyncpg.Connection):
    """Insert into auth.users (as Supabase Auth would); the trigger makes the profile."""

    async def _create(role: str = "student") -> uuid.UUID:
        user_id = uuid.uuid4()
        await raw_db.execute(
            "insert into auth.users (id, email) values ($1, $2)", user_id, f"{user_id}@example.edu"
        )
        if role != "student":
            await raw_db.execute(
                "update public.profiles set role = $1::public.user_role where id = $2",
                role,
                user_id,
            )
        return user_id

    return _create


@pytest.fixture
def consented_student(raw_db: asyncpg.Connection, create_user, settings: Settings):
    """A student who has accepted the terms for the current policy version."""

    async def _create() -> uuid.UUID:
        uid = await create_user()
        await raw_db.execute(
            "insert into public.consents (user_id, kind, granted, policy_version) "
            "values ($1, 'terms', true, $2)",
            uid,
            settings.current_policy_version,
        )
        return uid

    return _create
