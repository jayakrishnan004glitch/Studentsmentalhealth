from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient

from app.core.config import Settings, get_settings
from app.core.security import TokenVerifier
from app.db.session import make_engine, make_sessionmaker
from app.routers import health, journal, me, questionnaires, study

API_PREFIX = "/api/v1"


def build_token_verifier(settings: Settings) -> TokenVerifier:
    jwks = None
    if not settings.supabase_jwt_secret:
        jwks = PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=600, timeout=5)
    return TokenVerifier(
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        hs256_secret=settings.supabase_jwt_secret,
        jwks_client=jwks,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url)
        app.state.sessionmaker = make_sessionmaker(engine)
        app.state.settings = settings
        app.state.token_verifier = build_token_verifier(settings)
        yield
        await engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(health.router)
    app.include_router(me.router, prefix=API_PREFIX)
    app.include_router(journal.router, prefix=API_PREFIX)
    app.include_router(study.router, prefix=API_PREFIX)
    app.include_router(questionnaires.router, prefix=API_PREFIX)
    return app


app = create_app()
