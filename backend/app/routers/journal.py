from typing import Annotated, Literal

from fastapi import APIRouter, Query, status

from ai.responses import URGENT
from app.core.deps import ConsentedStudent, DbSession
from app.schemas.journal import JournalInsights, MoodLogCreate, MoodLogOut, MoodLogPage
from app.schemas.support import SupportOut
from app.services import journal as journal_service

router = APIRouter(prefix="/journal", tags=["journal"])

RANGES = {"7d": 7, "30d": 30, "90d": 90}

# Minutes east of UTC, as the client reports it (India = 330). Covers UTC-12..UTC+14.
TzOffset = Annotated[int, Query(ge=-720, le=840, description="Client UTC offset in minutes")]


@router.post("", response_model=MoodLogOut, status_code=status.HTTP_201_CREATED)
async def create_entry(body: MoodLogCreate, db: DbSession, user: ConsentedStudent) -> MoodLogOut:
    log, safety = await journal_service.create_log(db, user.profile.id, body)
    out = MoodLogOut.model_validate(log)
    if safety.flagged:
        out.support = SupportOut.of(URGENT)
    return out


@router.get("", response_model=MoodLogPage)
async def list_entries(
    db: DbSession,
    user: ConsentedStudent,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before_id: Annotated[int | None, Query(ge=1)] = None,
) -> MoodLogPage:
    rows, next_before = await journal_service.list_logs(
        db, user.profile.id, limit=limit, before_id=before_id
    )
    return MoodLogPage(
        items=[MoodLogOut.model_validate(r) for r in rows], next_before_id=next_before
    )


@router.get("/insights", response_model=JournalInsights)
async def get_insights(
    db: DbSession,
    user: ConsentedStudent,
    range_: Annotated[Literal["7d", "30d", "90d"], Query(alias="range")] = "7d",
    tz_offset_minutes: TzOffset = 0,
) -> JournalInsights:
    return await journal_service.insights(
        db, user.profile.id, range_days=RANGES[range_], offset_minutes=tz_offset_minutes
    )
