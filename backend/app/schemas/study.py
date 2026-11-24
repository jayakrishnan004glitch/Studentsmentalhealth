from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.db.models import StudyLinkKind


def _https_only(url: str) -> str:
    """Links open in the student's browser: only well-formed https URLs."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc or " " in url:
        raise ValueError("must be an https:// URL")
    return url


HttpsUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=9, max_length=2048),
    AfterValidator(_https_only),
]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
SourceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Module = Annotated[int, Field(ge=1, le=6)]


class SchemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str


class BranchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str


class CatalogOut(BaseModel):
    """Choices for the student's study profile."""

    schemes: list[SchemeOut]
    branches: list[BranchOut]
    semesters: list[int]


class SubjectOut(BaseModel):
    id: int
    scheme: str
    code: str
    name: str
    link_count: int


class SubjectListOut(BaseModel):
    scheme: str
    branch: str
    semester: int
    subjects: list[SubjectOut]


class StudyLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module: int | None
    kind: StudyLinkKind
    title: str
    url: str
    source_name: str | None


class SubjectDetailOut(BaseModel):
    id: int
    scheme: str
    code: str
    name: str
    # Sorted: whole-subject links first (module null), then modules 1..6.
    links: list[StudyLinkOut]


class StudyLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: int
    module: Module | None = None
    kind: StudyLinkKind
    title: Title
    url: HttpsUrl
    source_name: SourceName | None = None


class StudyLinkUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module: Module | None = None
    kind: StudyLinkKind | None = None
    title: Title | None = None
    url: HttpsUrl | None = None
    source_name: SourceName | None = None
    active: bool | None = None


class StudyLinkAdminOut(StudyLinkOut):
    subject_id: int
    active: bool
