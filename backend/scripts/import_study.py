"""Import KTU subjects and study links from CSV files.

Run from backend/ (uses DATABASE_URL from backend/.env unless --database-url):

    .venv/bin/python -m scripts.import_study \
        --subjects ../data/ktu/subjects.csv --links ../data/ktu/links.csv

Use --dry-run to validate the files without writing anything.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg

from app.core.config import get_settings
from app.services.study_import import (
    CsvImportError,
    import_catalog,
    parse_links,
    parse_subjects,
)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--subjects", type=Path, help="subjects CSV")
    parser.add_argument("--links", type=Path, help="links CSV")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--dry-run", action="store_true", help="validate only")
    args = parser.parse_args()
    if not args.subjects and not args.links:
        parser.error("give --subjects and/or --links")

    try:
        subjects = parse_subjects(args.subjects.read_text("utf-8")) if args.subjects else []
        links = parse_links(args.links.read_text("utf-8")) if args.links else []
    except CsvImportError as exc:
        print("CSV errors:\n  " + "\n  ".join(exc.errors), file=sys.stderr)
        return 1
    print(f"Parsed {len(subjects)} subject rows and {len(links)} link rows.")
    if args.dry_run:
        return 0

    dsn = (args.database_url or get_settings().database_url).replace("+asyncpg", "")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        report = await import_catalog(conn, subjects, links)
    except CsvImportError as exc:
        print("Nothing imported:\n  " + "\n  ".join(exc.errors), file=sys.stderr)
        return 1
    finally:
        await conn.close()
    print(
        f"Imported {report.subjects} subjects "
        f"({report.offerings_added} new branch/semester offerings) and {report.links} links."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
