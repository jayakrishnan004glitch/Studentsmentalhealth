from fastapi import APIRouter, HTTPException, status

from app.core.deps import AppSettings, AuthUser, DbSession
from app.schemas.me import ConsentRequest, MeOut, ProfileOut, ProfileUpdate
from app.services import consents as consent_service
from app.services import study as study_service

router = APIRouter(prefix="/me", tags=["me"])


async def _build_me(db: DbSession, user: AuthUser, settings: AppSettings) -> MeOut:
    policy = settings.current_policy_version
    states = await consent_service.current_consents(db, user.profile.id)
    missing = consent_service.missing_required(states, policy)
    return MeOut(
        profile=ProfileOut.model_validate(user.profile),
        consents=states,
        current_policy_version=policy,
        needs_consent=bool(missing),
        missing_consents=missing,
    )


@router.get("", response_model=MeOut)
async def get_me(db: DbSession, user: AuthUser, settings: AppSettings) -> MeOut:
    return await _build_me(db, user, settings)


@router.patch("", response_model=MeOut)
async def update_me(
    body: ProfileUpdate, db: DbSession, user: AuthUser, settings: AppSettings
) -> MeOut:
    changes = body.model_dump(exclude_unset=True)
    bad = await study_service.unknown_codes(
        db, scheme=changes.get("ktu_scheme"), branch=changes.get("branch")
    )
    if bad:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {"loc": ["body", f], "msg": "Unknown code", "type": "value_error"} for f in bad
            ],
        )
    for field, value in changes.items():
        setattr(user.profile, field, value)
    await db.commit()
    await db.refresh(user.profile)
    return await _build_me(db, user, settings)


@router.post("/consents", response_model=MeOut, status_code=status.HTTP_201_CREATED)
async def give_consents(
    body: ConsentRequest, db: DbSession, user: AuthUser, settings: AppSettings
) -> MeOut:
    policy = settings.current_policy_version
    if body.policy_version != policy:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Policy version is outdated; current version is {policy}",
        )
    await consent_service.record_consents(db, user.profile.id, body.items, policy)
    return await _build_me(db, user, settings)
