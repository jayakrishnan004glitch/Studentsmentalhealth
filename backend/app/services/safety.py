"""Records safety-rule hits. Week 3's SOS alert service turns these into
counsellor alerts; for now they are stored so nothing is lost."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SafetyEvent, SafetySource


def record_event(
    db: AsyncSession,
    user_id: UUID,
    source: SafetySource,
    source_id: int | None,
    categories: list[str] | tuple[str, ...],
) -> SafetyEvent:
    """Adds the event to the session; the caller commits (same transaction)."""
    event = SafetyEvent(
        user_id=user_id, source=source, source_id=source_id, categories=list(categories)
    )
    db.add(event)
    return event
