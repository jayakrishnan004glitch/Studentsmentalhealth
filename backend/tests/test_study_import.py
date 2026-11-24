import pytest

from app.services.study_import import (
    CsvImportError,
    import_catalog,
    parse_links,
    parse_subjects,
)

SUBJECTS = """scheme,code,name,semester,branches
2019,cst201,Data Structures,3,CSE;IT
# comment rows and blank lines are skipped

2019,MAT101,Linear Algebra and Calculus,1,ALL
"""

LINKS = """scheme,subject_code,module,kind,title,url,source_name
2019,CST201,1,notes,Module 1 notes,https://example.org/ds/m1,Example
2019,CST201,,syllabus,Syllabus,https://example.org/ds/syllabus,
"""


def test_parse_valid_files() -> None:
    subjects = parse_subjects("﻿" + SUBJECTS)  # Excel BOM is fine
    assert [(s.code, s.branches) for s in subjects] == [
        ("CST201", ["CSE", "IT"]),
        ("MAT101", ["ALL"]),
    ]
    links = parse_links(LINKS)
    assert links[0].module == 1
    assert links[1].module is None and links[1].source_name is None


def test_parse_reports_every_bad_line() -> None:
    bad = (
        "scheme,code,name,semester,branches\n19,CST201,Data Structures,3,CSE\n2019,CST202,,9,CSE\n"
    )
    with pytest.raises(CsvImportError) as exc:
        parse_subjects(bad)
    text = "\n".join(exc.value.errors)
    assert "line 2: scheme" in text
    assert "line 3: name" in text and "line 3: semester" in text


def test_parse_rejects_wrong_header_and_http_links() -> None:
    with pytest.raises(CsvImportError, match="header"):
        parse_subjects("code,name\nX,Y\n")
    with pytest.raises(CsvImportError, match="line 2: url"):
        parse_links(
            "scheme,subject_code,module,kind,title,url,source_name\n"
            "2019,CST201,1,notes,T,http://insecure.example,\n"
        )


async def test_import_is_idempotent_and_expands_all(raw_db) -> None:
    subjects, links = parse_subjects(SUBJECTS), parse_links(LINKS)
    first = await import_catalog(raw_db, subjects, links)
    branch_count = await raw_db.fetchval("select count(*) from public.ktu_branches")
    assert first.subjects == 2
    assert first.offerings_added == 2 + branch_count
    assert first.links == 2

    again = await import_catalog(raw_db, subjects, links)
    assert again.offerings_added == 0
    assert await raw_db.fetchval("select count(*) from public.study_links") == 2
    assert await raw_db.fetchval("select count(*) from public.ktu_subjects") == 2


async def test_links_can_be_imported_for_existing_subjects(raw_db) -> None:
    await import_catalog(raw_db, parse_subjects(SUBJECTS), [])
    report = await import_catalog(raw_db, [], parse_links(LINKS))
    assert report.links == 2


async def test_import_errors_roll_back_everything(raw_db) -> None:
    subjects = parse_subjects(
        "scheme,code,name,semester,branches\n"
        "2019,CST201,Data Structures,3,CSE\n"
        "2019,CST999,Bad branch,3,NOPE\n"
        "2030,CST998,Bad scheme,3,CSE\n"
    )
    links = parse_links(
        "scheme,subject_code,module,kind,title,url,source_name\n"
        "2019,ZZZ100,1,notes,Orphan,https://example.org/x,\n"
    )
    with pytest.raises(CsvImportError) as exc:
        await import_catalog(raw_db, subjects, links)
    text = "\n".join(exc.value.errors)
    assert "unknown branch(es) NOPE" in text
    assert "unknown scheme 2030" in text
    assert "no subject ZZZ100" in text
    assert await raw_db.fetchval("select count(*) from public.ktu_subjects") == 0
