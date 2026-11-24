"""KTU study catalogue: subjects per scheme/branch/semester and their links."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KtuBranch, KtuScheme, KtuSubject, KtuSubjectOffering, StudyLink
from app.schemas.study import (
    BranchOut,
    CatalogOut,
    SchemeOut,
    StudyLinkCreate,
    StudyLinkOut,
    StudyLinkUpdate,
    SubjectDetailOut,
    SubjectOut,
)

SEMESTERS = list(range(1, 9))


class DuplicateLinkError(Exception):
    """The subject already has a link with this URL."""


async def catalog(db: AsyncSession) -> CatalogOut:
    schemes = (await db.scalars(select(KtuScheme).order_by(KtuScheme.code.desc()))).all()
    branches = (await db.scalars(select(KtuBranch).order_by(KtuBranch.name))).all()
    return CatalogOut(
        schemes=[SchemeOut.model_validate(s) for s in schemes],
        branches=[BranchOut.model_validate(b) for b in branches],
        semesters=SEMESTERS,
    )


async def unknown_codes(db: AsyncSession, *, scheme: str | None, branch: str | None) -> list[str]:
    """Names of the profile fields whose code does not exist (empty if all valid)."""
    bad = []
    if scheme is not None and await db.get(KtuScheme, scheme) is None:
        bad.append("ktu_scheme")
    if branch is not None and await db.get(KtuBranch, branch) is None:
        bad.append("branch")
    return bad


async def subjects_for(
    db: AsyncSession, *, scheme: str, branch: str, semester: int
) -> list[SubjectOut]:
    link_count = (
        select(func.count())
        .where(StudyLink.subject_id == KtuSubject.id, StudyLink.active)
        .correlate(KtuSubject)
        .scalar_subquery()
    )
    stmt = (
        select(KtuSubject, link_count)
        .join(KtuSubjectOffering, KtuSubjectOffering.subject_id == KtuSubject.id)
        .where(
            KtuSubject.scheme == scheme,
            KtuSubjectOffering.branch == branch,
            KtuSubjectOffering.semester == semester,
        )
        .order_by(KtuSubject.code)
    )
    return [
        SubjectOut(id=s.id, scheme=s.scheme, code=s.code, name=s.name, link_count=n)
        for s, n in (await db.execute(stmt)).all()
    ]


async def subject_detail(db: AsyncSession, subject_id: int) -> SubjectDetailOut | None:
    subject = await db.get(KtuSubject, subject_id)
    if subject is None:
        return None
    links = (
        await db.scalars(
            select(StudyLink)
            .where(StudyLink.subject_id == subject_id, StudyLink.active)
            .order_by(StudyLink.module.asc().nulls_first(), StudyLink.kind, StudyLink.title)
        )
    ).all()
    return SubjectDetailOut(
        id=subject.id,
        scheme=subject.scheme,
        code=subject.code,
        name=subject.name,
        links=[StudyLinkOut.model_validate(link) for link in links],
    )


async def create_link(db: AsyncSession, body: StudyLinkCreate, created_by: UUID) -> StudyLink:
    link = StudyLink(**body.model_dump(), created_by=created_by)
    db.add(link)
    await _commit_or_duplicate(db)
    await db.refresh(link)
    return link


async def update_link(db: AsyncSession, link: StudyLink, body: StudyLinkUpdate) -> StudyLink:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(link, field, value)
    await _commit_or_duplicate(db)
    await db.refresh(link)
    return link


async def _commit_or_duplicate(db: AsyncSession) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "study_links_subject_id_url_key" in str(exc.orig):
            raise DuplicateLinkError from exc
        raise
