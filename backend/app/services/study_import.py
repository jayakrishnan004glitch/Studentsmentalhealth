"""Bulk import of the KTU catalogue from CSV (see data/ktu/README.md).

subjects.csv: scheme,code,name,semester,branches
    branches = "CSE;ECE;IT" or "ALL" (every branch in ktu_branches).
    A subject taken in different semesters by different branches gets one
    row per semester.
links.csv:    scheme,subject_code,module,kind,title,url,source_name
    module and source_name may be blank; module blank = whole subject.

Parsing is pure. Importing runs in ONE transaction: any error rolls back
everything, and re-running the same files is safe (upserts).
"""

import csv
import io
from dataclasses import dataclass
from typing import Annotated, TypeVar

import asyncpg
from pydantic import BaseModel, BeforeValidator, Field, StringConstraints, ValidationError

from app.db.models import StudyLinkKind
from app.schemas.study import HttpsUrl, Module, SourceName, Title

SUBJECT_HEADERS = ["scheme", "code", "name", "semester", "branches"]
LINK_HEADERS = ["scheme", "subject_code", "module", "kind", "title", "url", "source_name"]


class CsvImportError(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def _blank_to_none(v: object) -> object:
    return None if isinstance(v, str) and not v.strip() else v


def _split_branches(v: object) -> object:
    if isinstance(v, str):
        return [b.strip().upper() for b in v.split(";") if b.strip()]
    return v


Scheme = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{4}$")]
Code = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
    StringConstraints(pattern=r"^[A-Z0-9]{2,20}$"),
]


class SubjectRow(BaseModel):
    scheme: Scheme
    code: Code
    name: Title
    semester: Annotated[int, Field(ge=1, le=8)]
    branches: Annotated[list[str], BeforeValidator(_split_branches), Field(min_length=1)]


class LinkRow(BaseModel):
    scheme: Scheme
    subject_code: Code
    module: Annotated[Module | None, BeforeValidator(_blank_to_none)] = None
    kind: StudyLinkKind
    title: Title
    url: HttpsUrl
    source_name: Annotated[SourceName | None, BeforeValidator(_blank_to_none)] = None


T = TypeVar("T", bound=BaseModel)


def _parse(text: str, headers: list[str], model: type[T]) -> list[T]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))  # tolerate Excel's BOM
    if reader.fieldnames is None or [h.strip() for h in reader.fieldnames] != headers:
        raise CsvImportError([f"header must be exactly: {','.join(headers)}"])
    rows: list[T] = []
    errors: list[str] = []
    for line_no, raw in enumerate(reader, start=2):
        values = {k.strip(): (v or "") for k, v in raw.items() if k is not None}
        if not any(v.strip() for v in values.values()) or values[headers[0]].startswith("#"):
            continue  # blank line or comment
        try:
            rows.append(model.model_validate(values))
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(p) for p in err["loc"])
                errors.append(f"line {line_no}: {field}: {err['msg']}")
    if errors:
        raise CsvImportError(errors)
    return rows


def parse_subjects(text: str) -> list[SubjectRow]:
    return _parse(text, SUBJECT_HEADERS, SubjectRow)


def parse_links(text: str) -> list[LinkRow]:
    return _parse(text, LINK_HEADERS, LinkRow)


@dataclass(frozen=True)
class ImportReport:
    subjects: int
    offerings_added: int
    links: int


async def import_catalog(
    conn: asyncpg.Connection, subjects: list[SubjectRow], links: list[LinkRow]
) -> ImportReport:
    async with conn.transaction():
        schemes = {r["code"] for r in await conn.fetch("select code from public.ktu_schemes")}
        branches = {r["code"] for r in await conn.fetch("select code from public.ktu_branches")}
        errors: list[str] = []
        subject_ids: dict[tuple[str, str], int] = {}
        offerings_added = 0

        for s in subjects:
            if s.scheme not in schemes:
                errors.append(f"subject {s.code}: unknown scheme {s.scheme}")
                continue
            targets = sorted(branches) if s.branches == ["ALL"] else s.branches
            unknown = [b for b in targets if b not in branches]
            if unknown:
                errors.append(f"subject {s.code}: unknown branch(es) {', '.join(unknown)}")
                continue
            subject_id = await conn.fetchval(
                """
                insert into public.ktu_subjects (scheme, code, name) values ($1, $2, $3)
                on conflict (scheme, code) do update set name = excluded.name
                returning id
                """,
                s.scheme,
                s.code,
                s.name,
            )
            subject_ids[(s.scheme, s.code)] = subject_id
            for b in targets:
                status = await conn.execute(
                    """
                    insert into public.ktu_subject_offerings (subject_id, branch, semester)
                    values ($1, $2, $3) on conflict do nothing
                    """,
                    subject_id,
                    b,
                    s.semester,
                )
                offerings_added += status == "INSERT 0 1"

        link_count = 0
        for link in links:
            key = (link.scheme, link.subject_code)
            subject_id = subject_ids.get(key) or await conn.fetchval(
                "select id from public.ktu_subjects where scheme = $1 and code = $2", *key
            )
            if subject_id is None:
                errors.append(
                    f"link {link.url}: no subject {link.subject_code} in scheme {link.scheme}"
                )
                continue
            await conn.execute(
                """
                insert into public.study_links
                  (subject_id, module, kind, title, url, source_name)
                values ($1, $2, $3, $4, $5, $6)
                on conflict (subject_id, url) do update set
                  module = excluded.module, kind = excluded.kind, title = excluded.title,
                  source_name = excluded.source_name, active = true
                """,
                subject_id,
                link.module,
                link.kind.value,
                link.title,
                link.url,
                link.source_name,
            )
            link_count += 1

        if errors:
            raise CsvImportError(errors)  # rolls the transaction back
    return ImportReport(
        subjects=len(subject_ids), offerings_added=offerings_added, links=link_count
    )
