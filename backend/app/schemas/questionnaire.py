from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ai.scoring import Instrument
from app.schemas.support import SupportOut


class QuestionnaireSummary(BaseModel):
    instrument: Instrument
    name: str
    short_name: str
    description: str
    item_count: int
    minutes: int
    last_taken_at: datetime | None
    last_severity_label: str | None


class QuestionnaireDefinition(BaseModel):
    instrument: Instrument
    name: str
    short_name: str
    stem: str
    options: list[str]  # index = score for that option
    items: list[str]


class AnswersIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Length and range are checked per instrument by ai.scoring.validate_answers.
    answers: Annotated[list[int], Field(min_length=1, max_length=50)]


class SubscaleOut(BaseModel):
    code: str
    label: str
    score: int
    severity: str
    severity_label: str
    level: int


class QuestionnaireResultOut(BaseModel):
    id: int
    instrument: Instrument
    total: int
    max_total: int
    severity: str
    severity_label: str
    level: int
    max_level: int
    subscales: list[SubscaleOut]
    item9_flag: bool
    created_at: datetime
    # Only on the submit response.
    support: SupportOut | None = None


class ResultHistoryItem(BaseModel):
    id: int
    total: int
    severity: str
    level: int
    created_at: datetime
