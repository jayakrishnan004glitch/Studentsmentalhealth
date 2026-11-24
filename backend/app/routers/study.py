from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.deps import AuthUser, ConsentedStudent, CurrentUser, DbSession, require_roles
from app.db.models import KtuSubject, StudyLink, UserRole
from app.schemas.study import (
    CatalogOut,
    StudyLinkAdminOut,
    StudyLinkCreate,
    StudyLinkUpdate,
    SubjectDetailOut,
    SubjectListOut,
)
from app.services import study as study_service

router = APIRouter(prefix="/study", tags=["study"])

Admin = Annotated[CurrentUser, Depends(require_roles(UserRole.admin))]

PROFILE_INCOMPLETE = "Set your KTU scheme, branch and semester first"


# ------------------------------------------------------------------ students


@router.get("/catalog", response_model=CatalogOut)
async def get_catalog(db: DbSession, user: AuthUser) -> CatalogOut:
    """Schemes, branches and semesters for the study-profile picker."""
    return await study_service.catalog(db)


@router.get("/subjects", response_model=SubjectListOut)
async def list_subjects(
    db: DbSession,
    user: ConsentedStudent,
    scheme: Annotated[str | None, Query(pattern=r"^[0-9]{4}$")] = None,
    branch: Annotated[str | None, Query(max_length=5)] = None,
    semester: Annotated[int | None, Query(ge=1, le=8)] = None,
) -> SubjectListOut:
    """Subjects for the student's own semester; query params browse others
    (e.g. a supplementary exam from an earlier semester)."""
    p = user.profile
    scheme = scheme or p.ktu_scheme
    branch = (branch or p.branch or "").upper() or None
    semester = semester or p.semester
    if scheme is None or branch is None or semester is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=PROFILE_INCOMPLETE)
    subjects = await study_service.subjects_for(db, scheme=scheme, branch=branch, semester=semester)
    return SubjectListOut(scheme=scheme, branch=branch, semester=semester, subjects=subjects)


@router.get("/subjects/{subject_id}", response_model=SubjectDetailOut)
async def get_subject(subject_id: int, db: DbSession, user: ConsentedStudent) -> SubjectDetailOut:
    detail = await study_service.subject_detail(db, subject_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return detail


# ------------------------------------------------------------------ admins


@router.post("/links", response_model=StudyLinkAdminOut, status_code=status.HTTP_201_CREATED)
async def create_link(body: StudyLinkCreate, db: DbSession, admin: Admin) -> StudyLinkAdminOut:
    if await db.get(KtuSubject, body.subject_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Subject not found")
    try:
        link = await study_service.create_link(db, body, admin.profile.id)
    except study_service.DuplicateLinkError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This subject already has that link"
        ) from None
    return StudyLinkAdminOut.model_validate(link)


async def _get_link(db: DbSession, link_id: int) -> StudyLink:
    link = await db.get(StudyLink, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Link not found")
    return link


@router.patch("/links/{link_id}", response_model=StudyLinkAdminOut)
async def update_link(
    link_id: int, body: StudyLinkUpdate, db: DbSession, admin: Admin
) -> StudyLinkAdminOut:
    link = await _get_link(db, link_id)
    try:
        link = await study_service.update_link(db, link, body)
    except study_service.DuplicateLinkError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This subject already has that link"
        ) from None
    return StudyLinkAdminOut.model_validate(link)


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: int, db: DbSession, admin: Admin) -> Response:
    await db.delete(await _get_link(db, link_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
