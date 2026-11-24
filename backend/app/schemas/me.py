from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.db.models import ConsentKind, UserRole

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    display_name: str | None
    department: str | None
    year: int | None
    ktu_scheme: str | None
    branch: str | None
    semester: int | None
    pseudonym: str
    created_at: datetime


class ProfileUpdate(BaseModel):
    """Fields a student may change. Role and pseudonym are not editable."""

    model_config = ConfigDict(extra="forbid")

    display_name: Annotated[ShortText, StringConstraints(max_length=50)] | None = None
    department: Annotated[ShortText, StringConstraints(max_length=80)] | None = None
    year: Annotated[int, Field(ge=1, le=6)] | None = None
    # Must exist in ktu_schemes / ktu_branches (checked by the router).
    ktu_scheme: Annotated[str, StringConstraints(pattern=r"^[0-9]{4}$")] | None = None
    branch: (
        Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, max_length=5)] | None
    ) = None
    semester: Annotated[int, Field(ge=1, le=8)] | None = None


class ConsentState(BaseModel):
    kind: ConsentKind
    granted: bool
    policy_version: str
    updated_at: datetime


class ConsentItem(BaseModel):
    kind: ConsentKind
    granted: bool


class ConsentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_version: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    items: Annotated[list[ConsentItem], Field(min_length=1, max_length=len(ConsentKind))]

    @field_validator("items")
    @classmethod
    def kinds_unique(cls, items: list[ConsentItem]) -> list[ConsentItem]:
        kinds = [i.kind for i in items]
        if len(kinds) != len(set(kinds)):
            raise ValueError("each consent kind may appear only once")
        return items


class MeOut(BaseModel):
    profile: ProfileOut
    consents: list[ConsentState]
    current_policy_version: str
    # True until the student has accepted the required consents for the
    # current policy version. Clients show the consent screen while true.
    needs_consent: bool
    missing_consents: list[ConsentKind]
