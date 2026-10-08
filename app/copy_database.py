"""Copy every resume row from a SQLite file into another database, keeping IDs.

Usage: uv run python -m app.copy_database data/resume.db [--target-env NAME]
The target URL is read from an environment variable (default
RAILWAY_DATABASE_URL, loaded from .env) so it never appears in shell history.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import URL, func, select, text
from sqlalchemy.engine import Connection, Engine

from app.database import Base, create_database_engine

STARTER_PROFILE = {
    "slug": "owner",
    "display_name": "Your Name",
    "headline": "Business Analytics Senior",
    "summary": "Add a short professional summary.",
}


class TargetNotEmptyError(RuntimeError):
    pass


def _holds_only_starter_profile(connection: Connection) -> bool:
    profiles = Base.metadata.tables["profiles"]
    for table in Base.metadata.sorted_tables:
        if table is not profiles and connection.scalar(
            select(func.count()).select_from(table)
        ):
            return False
    rows = connection.execute(select(profiles)).mappings().all()
    if not rows:
        return True
    return len(rows) == 1 and all(
        rows[0][key] == value for key, value in STARTER_PROFILE.items()
    )


def copy_database(source: Engine, target: Engine) -> dict[str, int]:
    Base.metadata.create_all(target)
    counts: dict[str, int] = {}
    with source.connect() as reader, target.begin() as writer:
        if not _holds_only_starter_profile(writer):
            raise TargetNotEmptyError(
                "Target database already has resume content; nothing was copied."
            )
        writer.execute(Base.metadata.tables["profiles"].delete())
        for table in Base.metadata.sorted_tables:
            rows = [dict(row) for row in reader.execute(select(table)).mappings()]
            if rows:
                writer.execute(table.insert(), rows)
            counts[table.name] = len(rows)
        if target.dialect.name == "postgresql":
            for table in Base.metadata.sorted_tables:
                if "id" in table.c:
                    writer.execute(
                        text(
                            f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                            f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table.name}"
                        )
                    )
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", help="path to the SQLite database to copy from")
    parser.add_argument(
        "--target-env",
        default="RAILWAY_DATABASE_URL",
        help="environment variable that holds the target database URL",
    )
    args = parser.parse_args(argv)

    source_path = Path(args.source).expanduser().resolve()
    if not source_path.is_file():
        print(f"Source database {source_path} does not exist.", file=sys.stderr)
        return 2
    target_url = os.getenv(args.target_env)
    if not target_url:
        print(f"{args.target_env} is not set.", file=sys.stderr)
        return 2

    source = create_database_engine(
        URL.create("sqlite", database=str(source_path)).render_as_string()
    )
    target = create_database_engine(target_url)
    try:
        counts = copy_database(source, target)
    except TargetNotEmptyError as error:
        print(error, file=sys.stderr)
        return 1
    finally:
        source.dispose()
        target.dispose()

    for table_name, count in counts.items():
        print(f"{table_name}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
