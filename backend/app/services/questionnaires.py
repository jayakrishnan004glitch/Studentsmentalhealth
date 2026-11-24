from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from ai import scoring
from ai.responses import SUGGEST, URGENT
from ai.scoring import DEFINITIONS, Instrument, ScoreResult
from app.db.models import QuestionnaireResult, SafetySource
from app.schemas.questionnaire import (
    QuestionnaireDefinition,
    QuestionnaireResultOut,
    QuestionnaireSummary,
    ResultHistoryItem,
    SubscaleOut,
)
from app.schemas.support import SupportOut
from app.services import safety as safety_service

ITEM9_CATEGORY = "phq9_item9"


def definition(instrument: Instrument) -> QuestionnaireDefinition:
    d = DEFINITIONS[instrument]
    return QuestionnaireDefinition(
        instrument=d.instrument,
        name=d.name,
        short_name=d.short_name,
        stem=d.stem,
        options=list(d.options),
        items=list(d.items),
    )


async def summaries(db: AsyncSession, user_id: UUID) -> list[QuestionnaireSummary]:
    latest = (
        await db.scalars(
            select(QuestionnaireResult)
            .where(QuestionnaireResult.user_id == user_id)
            .ext(distinct_on(QuestionnaireResult.instrument))
            .order_by(QuestionnaireResult.instrument, QuestionnaireResult.created_at.desc())
        )
    ).all()
    last = {r.instrument: r for r in latest}
    out = []
    for inst, d in DEFINITIONS.items():
        r = last.get(inst)
        out.append(
            QuestionnaireSummary(
                instrument=inst,
                name=d.name,
                short_name=d.short_name,
                description=d.description,
                item_count=len(d.items),
                minutes=d.minutes,
                last_taken_at=r.created_at if r else None,
                last_severity_label=r.score.get("severity_label") if r else None,
            )
        )
    return out


def _to_out(row: QuestionnaireResult, result: ScoreResult) -> QuestionnaireResultOut:
    return QuestionnaireResultOut(
        id=row.id,
        instrument=result.instrument,
        total=result.total,
        max_total=result.max_total,
        severity=result.severity,
        severity_label=result.severity_label,
        level=result.level,
        max_level=result.max_level,
        subscales=[SubscaleOut(**s.__dict__) for s in result.subscales],
        item9_flag=result.item9_flag,
        created_at=row.created_at,
    )


async def submit(
    db: AsyncSession, user_id: UUID, instrument: Instrument, answers: list[int]
) -> QuestionnaireResultOut:
    """Scores and stores a submission. Raises scoring.InvalidAnswers."""
    result = scoring.score(instrument, answers)
    row = QuestionnaireResult(
        user_id=user_id,
        instrument=instrument,
        answers=answers,
        score={
            "total": result.total,
            "severity_label": result.severity_label,
            "subscales": {s.code: s.score for s in result.subscales},
        },
        severity=result.severity,
        level=result.level,
        item9_flag=result.item9_flag,
    )
    db.add(row)
    await db.flush()  # assigns row.id for the safety event
    if result.item9_flag:
        safety_service.record_event(
            db, user_id, SafetySource.questionnaire, row.id, [ITEM9_CATEGORY]
        )
    await db.commit()
    await db.refresh(row)

    out = _to_out(row, result)
    if result.item9_flag:
        out.support = SupportOut.of(URGENT)
    elif scoring.suggests_support(result):
        out.support = SupportOut.of(SUGGEST)
    return out


async def history(
    db: AsyncSession, user_id: UUID, instrument: Instrument, limit: int
) -> list[ResultHistoryItem]:
    rows = (
        await db.scalars(
            select(QuestionnaireResult)
            .where(
                QuestionnaireResult.user_id == user_id,
                QuestionnaireResult.instrument == instrument,
            )
            .order_by(QuestionnaireResult.created_at.desc(), QuestionnaireResult.id.desc())
            .limit(limit)
        )
    ).all()
    return [
        ResultHistoryItem(
            id=r.id,
            total=r.score["total"],
            severity=r.severity,
            level=r.level,
            created_at=r.created_at,
        )
        for r in rows
    ]
