import enum
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.support import SupportOut


class MoodTag(enum.StrEnum):
    """What a mood entry is about. Kept in the API (not the DB) so it can grow."""

    exams = "exams"
    assignments = "assignments"
    classes = "classes"
    family = "family"
    friends = "friends"
    relationship = "relationship"
    health = "health"
    sleep = "sleep"
    money = "money"
    homesick = "homesick"
    placements = "placements"
    other = "other"


class MoodLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mood_score: Annotated[int, Field(ge=1, le=5)]
    sleep_hours: Annotated[float, Field(ge=0, le=24)] | None = None
    energy: Annotated[int, Field(ge=1, le=5)] | None = None
    tags: Annotated[list[MoodTag], Field(max_length=10)] = Field(default_factory=list)
    note: Annotated[str, Field(max_length=1000)] | None = None

    @field_validator("sleep_hours")
    @classmethod
    def one_decimal(cls, v: float | None) -> float | None:
        return None if v is None else round(v, 1)

    @field_validator("tags")
    @classmethod
    def dedupe(cls, tags: list[MoodTag]) -> list[MoodTag]:
        return list(dict.fromkeys(tags))

    @field_validator("note")
    @classmethod
    def blank_note_is_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class MoodLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mood_score: int
    sleep_hours: float | None
    energy: int | None
    tags: list[str]
    note: str | None
    created_at: datetime
    # Only on the create response: set when the note triggered the safety rules.
    support: SupportOut | None = None


class MoodLogPage(BaseModel):
    items: list[MoodLogOut]
    # Pass as `before_id` to fetch the next (older) page; null on the last page.
    next_before_id: int | None


class DaySummary(BaseModel):
    date: date
    entries: int
    mood_avg: float | None
    sleep_avg: float | None


class TagCount(BaseModel):
    tag: str
    count: int


class JournalInsights(BaseModel):
    range_days: int
    # One item per local day in the range, oldest first; empty days have
    # entries=0 and null averages so charts can show gaps.
    days: list[DaySummary]
    entries: int
    mood_avg: float | None
    sleep_avg: float | None
    # Consecutive local days with at least one entry, ending today (or
    # yesterday, if the student has not logged yet today).
    streak_days: int
    top_tags: list[TagCount]
