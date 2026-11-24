"""SQLAlchemy models that MIRROR tables created by supabase/migrations.

The schema is owned by the SQL migrations (Supabase CLI). Never call
Base.metadata.create_all() against Supabase.
"""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    FetchedValue,
    ForeignKey,
    Numeric,
    SmallInteger,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ai.scoring import Instrument


class Base(DeclarativeBase):
    pass


class UserRole(enum.StrEnum):
    student = "student"
    counsellor = "counsellor"
    admin = "admin"


class ConsentKind(enum.StrEnum):
    terms = "terms"
    ai_processing = "ai_processing"
    camera = "camera"
    microphone = "microphone"
    counsellor_contact = "counsellor_contact"


def _pg_enum(cls: type[enum.Enum], name: str) -> Enum:
    return Enum(
        cls,
        name=name,
        schema="public",
        create_type=False,
        values_callable=lambda e: [m.value for m in e],
    )


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(
        _pg_enum(UserRole, "user_role"), server_default=FetchedValue()
    )
    display_name: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    year: Mapped[int | None] = mapped_column(SmallInteger)
    # KTU study profile: decides which subjects the student sees.
    ktu_scheme: Mapped[str | None] = mapped_column(ForeignKey("public.ktu_schemes.code"))
    branch: Mapped[str | None] = mapped_column(ForeignKey("public.ktu_branches.code"))
    semester: Mapped[int | None] = mapped_column(SmallInteger)
    pseudonym: Mapped[str] = mapped_column(Text, server_default=FetchedValue())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )
    # Set by the profiles_set_updated_at trigger.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue(), server_onupdate=FetchedValue()
    )


class StudyLinkKind(enum.StrEnum):
    notes = "notes"
    question_paper = "question_paper"
    syllabus = "syllabus"
    video = "video"
    textbook = "textbook"
    other = "other"


class KtuScheme(Base):
    __tablename__ = "ktu_schemes"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)


class KtuBranch(Base):
    __tablename__ = "ktu_branches"
    __table_args__ = {"schema": "public"}

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)


class KtuSubject(Base):
    __tablename__ = "ktu_subjects"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scheme: Mapped[str] = mapped_column(ForeignKey("public.ktu_schemes.code"))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)


class KtuSubjectOffering(Base):
    __tablename__ = "ktu_subject_offerings"
    __table_args__ = {"schema": "public"}

    subject_id: Mapped[int] = mapped_column(ForeignKey("public.ktu_subjects.id"), primary_key=True)
    branch: Mapped[str] = mapped_column(ForeignKey("public.ktu_branches.code"), primary_key=True)
    semester: Mapped[int] = mapped_column(SmallInteger, primary_key=True)


class StudyLink(Base):
    __tablename__ = "study_links"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("public.ktu_subjects.id"))
    module: Mapped[int | None] = mapped_column(SmallInteger)
    kind: Mapped[StudyLinkKind] = mapped_column(_pg_enum(StudyLinkKind, "study_link_kind"))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, server_default=FetchedValue())
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("public.profiles.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue(), server_onupdate=FetchedValue()
    )


class MoodLog(Base):
    __tablename__ = "mood_logs"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("public.profiles.id"))
    mood_score: Mapped[int] = mapped_column(SmallInteger)
    sleep_hours: Mapped[float | None] = mapped_column(Numeric(3, 1, asdecimal=False))
    energy: Mapped[int | None] = mapped_column(SmallInteger)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=FetchedValue())
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("public.profiles.id"))
    kind: Mapped[ConsentKind] = mapped_column(_pg_enum(ConsentKind, "consent_kind"))
    granted: Mapped[bool] = mapped_column(Boolean)
    policy_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )


class SafetySource(enum.StrEnum):
    journal = "journal"
    questionnaire = "questionnaire"
    chat = "chat"
    sos = "sos"


class QuestionnaireResult(Base):
    __tablename__ = "questionnaire_results"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("public.profiles.id"))
    instrument: Mapped[Instrument] = mapped_column(_pg_enum(Instrument, "questionnaire_instrument"))
    answers: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    score: Mapped[dict] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(Text)
    level: Mapped[int] = mapped_column(SmallInteger)
    item9_flag: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )


class SafetyEvent(Base):
    __tablename__ = "safety_events"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("public.profiles.id"))
    source: Mapped[SafetySource] = mapped_column(_pg_enum(SafetySource, "safety_source"))
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    categories: Mapped[list[str]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )
