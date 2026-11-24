from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.security import InvalidTokenError, TokenClaims, TokenVerifier
from app.db.models import Profile, UserRole
from app.services import consents as consent_service

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


async def get_token_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> TokenClaims:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        # PyJWKClient may fetch keys over HTTP (cached afterwards); run it off
        # the event loop.
        return await run_in_threadpool(verifier.verify, credentials.credentials)
    except InvalidTokenError:
        raise unauthorized from None


@dataclass(frozen=True)
class CurrentUser:
    claims: TokenClaims
    profile: Profile

    @property
    def role(self) -> UserRole:
        return self.profile.role


async def get_current_user(
    claims: Annotated[TokenClaims, Depends(get_token_claims)],
    db: DbSession,
) -> CurrentUser:
    profile = await db.get(Profile, claims.user_id)
    if profile is None:
        # Token is valid but the sign-up trigger has not created a profile
        # (or the account was deleted).
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Profile not found")
    return CurrentUser(claims=claims, profile=profile)


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]


async def get_consented_student(
    user: AuthUser, db: DbSession, settings: AppSettings
) -> CurrentUser:
    """A student who has accepted the required consents for the current policy.

    Every route that stores a student's wellbeing data depends on this, so no
    data is collected before consent (or after a policy change, until re-consent).
    """
    if user.role != UserRole.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Students only")
    states = await consent_service.current_consents(db, user.profile.id)
    if consent_service.missing_required(states, settings.current_policy_version):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Consent required")
    return user


ConsentedStudent = Annotated[CurrentUser, Depends(get_consented_student)]


def require_roles(*roles: UserRole) -> Callable[..., CurrentUser]:
    """Dependency factory: `Depends(require_roles(UserRole.counsellor))`."""

    async def checker(user: AuthUser) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return checker
