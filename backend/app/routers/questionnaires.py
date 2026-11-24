from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from ai.scoring import Instrument, InvalidAnswers
from app.core.deps import ConsentedStudent, DbSession
from app.schemas.questionnaire import (
    AnswersIn,
    QuestionnaireDefinition,
    QuestionnaireResultOut,
    QuestionnaireSummary,
    ResultHistoryItem,
)
from app.services import questionnaires as q_service

router = APIRouter(prefix="/questionnaires", tags=["questionnaires"])


@router.get("", response_model=list[QuestionnaireSummary])
async def list_questionnaires(db: DbSession, user: ConsentedStudent) -> list[QuestionnaireSummary]:
    return await q_service.summaries(db, user.profile.id)


@router.get("/{instrument}", response_model=QuestionnaireDefinition)
async def get_questionnaire(
    instrument: Instrument, user: ConsentedStudent
) -> QuestionnaireDefinition:
    return q_service.definition(instrument)


@router.post(
    "/{instrument}", response_model=QuestionnaireResultOut, status_code=status.HTTP_201_CREATED
)
async def submit_questionnaire(
    instrument: Instrument, body: AnswersIn, db: DbSession, user: ConsentedStudent
) -> QuestionnaireResultOut:
    try:
        return await q_service.submit(db, user.profile.id, instrument, body.answers)
    except InvalidAnswers as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from None


@router.get("/{instrument}/results", response_model=list[ResultHistoryItem])
async def result_history(
    instrument: Instrument,
    db: DbSession,
    user: ConsentedStudent,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ResultHistoryItem]:
    return await q_service.history(db, user.profile.id, instrument, limit)
