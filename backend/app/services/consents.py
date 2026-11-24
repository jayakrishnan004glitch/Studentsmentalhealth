from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Consent, ConsentKind
from app.schemas.me import ConsentItem, ConsentState

# Consents a student must grant (for the current policy version) to use the app.
REQUIRED_CONSENTS: tuple[ConsentKind, ...] = (ConsentKind.terms,)


async def current_consents(db: AsyncSession, user_id: UUID) -> list[ConsentState]:
    """Latest row per consent kind (the consent log is append-only)."""
    stmt = (
        select(Consent)
        .where(Consent.user_id == user_id)
        .ext(distinct_on(Consent.kind))
        .order_by(Consent.kind, Consent.created_at.desc(), Consent.id.desc())
    )
    rows = (await db.scalars(stmt)).all()
    return [
        ConsentState(
            kind=r.kind, granted=r.granted, policy_version=r.policy_version, updated_at=r.created_at
        )
        for r in rows
    ]


def missing_required(states: list[ConsentState], policy_version: str) -> list[ConsentKind]:
    granted = {s.kind for s in states if s.granted and s.policy_version == policy_version}
    return [k for k in REQUIRED_CONSENTS if k not in granted]


async def record_consents(
    db: AsyncSession, user_id: UUID, items: list[ConsentItem], policy_version: str
) -> None:
    db.add_all(
        Consent(user_id=user_id, kind=i.kind, granted=i.granted, policy_version=policy_version)
        for i in items
    )
    await db.commit()
