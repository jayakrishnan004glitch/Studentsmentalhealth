"""Mood & sleep journal: storage queries plus pure insight calculations.

Days are the student's *local* days. The client sends its UTC offset in
minutes (e.g. +330 for India); timestamps are stored in UTC.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.safety import SafetyResult, check_text
from app.db.models import MoodLog, SafetySource
from app.schemas.journal import DaySummary, JournalInsights, MoodLogCreate, TagCount
from app.services import safety as safety_service

STREAK_LOOKBACK_DAYS = 366
TOP_TAGS = 5


# ------------------------------------------------------------------ pure logic


@dataclass(frozen=True)
class DayRow:
    day: date
    entries: int
    mood_sum: float
    sleep_sum: float
    sleep_entries: int


def local_today(now_utc: datetime, offset_minutes: int) -> date:
    return (now_utc + timedelta(minutes=offset_minutes)).date()


def local_day_start_utc(day: date, offset_minutes: int) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC) - timedelta(minutes=offset_minutes)


def streak(logged_days: Iterable[date], today: date) -> int:
    days = set(logged_days)
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def _avg(total: float, n: int) -> float | None:
    return round(total / n, 2) if n else None


def build_insights(
    *,
    today: date,
    range_days: int,
    rows: Iterable[DayRow],
    logged_days: Iterable[date],
    tag_counts: Iterable[tuple[str, int]],
) -> JournalInsights:
    by_day = {r.day: r for r in rows}
    start = today - timedelta(days=range_days - 1)
    days: list[DaySummary] = []
    entries = mood_sum = sleep_sum = sleep_n = 0
    for i in range(range_days):
        d = start + timedelta(days=i)
        r = by_day.get(d)
        if r is None:
            days.append(DaySummary(date=d, entries=0, mood_avg=None, sleep_avg=None))
            continue
        days.append(
            DaySummary(
                date=d,
                entries=r.entries,
                mood_avg=_avg(r.mood_sum, r.entries),
                sleep_avg=_avg(r.sleep_sum, r.sleep_entries),
            )
        )
        entries += r.entries
        mood_sum += r.mood_sum
        sleep_sum += r.sleep_sum
        sleep_n += r.sleep_entries

    top = sorted(tag_counts, key=lambda tc: (-tc[1], tc[0]))[:TOP_TAGS]
    return JournalInsights(
        range_days=range_days,
        days=days,
        entries=entries,
        mood_avg=_avg(mood_sum, entries),
        sleep_avg=_avg(sleep_sum, sleep_n),
        streak_days=streak(logged_days, today),
        top_tags=[TagCount(tag=t, count=c) for t, c in top],
    )


# ------------------------------------------------------------------ queries


async def create_log(
    db: AsyncSession, user_id: UUID, body: MoodLogCreate
) -> tuple[MoodLog, SafetyResult]:
    """Stores the entry; the note goes through the safety rules first."""
    safety = check_text(body.note)
    log = MoodLog(
        user_id=user_id,
        mood_score=body.mood_score,
        sleep_hours=body.sleep_hours,
        energy=body.energy,
        tags=[t.value for t in body.tags],
        note=body.note,
    )
    db.add(log)
    if safety.flagged:
        await db.flush()  # assigns log.id
        safety_service.record_event(db, user_id, SafetySource.journal, log.id, safety.categories)
    await db.commit()
    await db.refresh(log)
    return log, safety


async def list_logs(
    db: AsyncSession, user_id: UUID, *, limit: int, before_id: int | None
) -> tuple[list[MoodLog], int | None]:
    stmt = select(MoodLog).where(MoodLog.user_id == user_id)
    if before_id is not None:
        stmt = stmt.where(MoodLog.id < before_id)
    stmt = stmt.order_by(MoodLog.id.desc()).limit(limit + 1)
    rows = list((await db.scalars(stmt)).all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    return rows, (rows[-1].id if has_more else None)


def _local_date(offset_minutes: int):
    # timezone('UTC', timestamptz) -> naive UTC timestamp; shift; take the date.
    return cast(func.timezone("UTC", MoodLog.created_at) + timedelta(minutes=offset_minutes), Date)


async def insights(
    db: AsyncSession,
    user_id: UUID,
    *,
    range_days: int,
    offset_minutes: int,
    now_utc: datetime | None = None,
) -> JournalInsights:
    today = local_today(now_utc or datetime.now(UTC), offset_minutes)
    range_start = local_day_start_utc(today - timedelta(days=range_days - 1), offset_minutes)
    streak_start = local_day_start_utc(today - timedelta(days=STREAK_LOOKBACK_DAYS), offset_minutes)
    day = _local_date(offset_minutes).label("day")
    mine = MoodLog.user_id == user_id

    daily = await db.execute(
        select(
            day,
            func.count(),
            func.sum(MoodLog.mood_score),
            func.coalesce(func.sum(MoodLog.sleep_hours), 0),
            func.count(MoodLog.sleep_hours),
        )
        .where(mine, MoodLog.created_at >= range_start)
        .group_by(day)
    )
    rows = [
        DayRow(day=d, entries=n, mood_sum=float(m), sleep_sum=float(s), sleep_entries=sn)
        for d, n, m, s, sn in daily.all()
    ]

    logged = await db.scalars(
        select(day).where(mine, MoodLog.created_at >= streak_start).distinct()
    )

    tag = func.unnest(MoodLog.tags).label("tag")
    tags_sub = select(tag).where(mine, MoodLog.created_at >= range_start).subquery()
    tag_rows = await db.execute(select(tags_sub.c.tag, func.count()).group_by(tags_sub.c.tag))

    return build_insights(
        today=today,
        range_days=range_days,
        rows=rows,
        logged_days=logged.all(),
        tag_counts=[(t, c) for t, c in tag_rows.all()],
    )
