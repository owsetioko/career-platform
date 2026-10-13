# Railway + PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve `csetioko.me` from the existing Railway project's web service, reading Chris's resume content from the project's PostgreSQL service instead of SQLite on the Azure VM.

**Architecture:** The app code stays one FastAPI process. `app/database.py` learns to accept Railway's `postgresql://` URL and connect through psycopg 3. A small one-shot command copies every row from the current SQLite file into Railway Postgres, keeping row IDs and resetting Postgres sequences. Railway builds from GitHub with Railpack (uv + `uv.lock`), runs `python -m app.database` as a pre-deploy step, and starts Uvicorn with proxy headers trusted, because Railway terminates TLS in front of the app. DNS for `csetioko.me` moves from the VM's IP to Railway in Cloudflare. The VM stays running untouched as the rollback path.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, psycopg 3 (`psycopg[binary]`), PostgreSQL (Railway), Railpack, Railway CLI, Cloudflare DNS, uv.

**Spec:** Chris's request on 2026-10-08 ("move it to Railway and PostgreSQL; the Railway project already exists with Postgres and a web service"), plus the inspection findings below.

## Inspection findings (2026-10-08)

- **Running site:** `career-platform.service` on `vm-career-platform` (20.88.61.1), commit `83c7eb6`. It runs `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2` behind Nginx + Let's Encrypt for `csetioko.me` and `www.csetioko.me`.
- **VM environment:** only `APP_TITLE` and `DATABASE_URL` are set. `SESSION_SECRET` and `ADMIN_PASSWORD_HASH` are not, so **admin is disabled in production today**. This plan keeps it disabled.
- **Data:** the VM's `data/resume.db` and the laptop's `data/resume.db` have identical `.dump` hashes (`8989f2cf…`). They hold 1 profile, 5 experiences, 15 skills, 3 projects, 0 project tags, 3 education rows, 8 experience-skill links, and 4 project-skill links. `/data/` is git-ignored, so the data never reaches GitHub or the Railway build.
- **Postgres blockers in the code:**
  1. Railway's `DATABASE_URL` starts with `postgresql://`. SQLAlchemy maps that to `psycopg2`, which isn't installed, so the app would crash on start.
  2. `_add_missing_content_display_columns` uses `BOOLEAN NOT NULL DEFAULT 1`. Postgres rejects that (integer default on a boolean column). A fresh database never hits that path, but it is a latent bug.
  3. Templates use `url_for('static', …)`, which builds absolute URLs. Behind Railway's TLS proxy, without trusted proxy headers, those URLs would be `http://…`. Browsers block them as mixed content, so the page would render without CSS or fonts.
- **Ephemeral disk:** `data/public-profile.json` (the last-good snapshot) is written to the container's disk. Railway wipes it on every deploy. If Postgres is unreachable on a freshly deployed container, visitors see the bundled starter profile ("Your Name"). This plan accepts that trade-off: a Railway volume would add downtime to every deploy.
- **Local `.env`:** holds `RAILWAY_DATABASE_URL`, which is Railway's **public** proxy URL (`tramway.proxy.rlwy.net:29364`, database `railway`). It is used only for the one-time copy from the laptop. The deployed app uses the private URL through a Railway variable reference.
- **Tooling:** `uv` 0.12 and Homebrew are installed. The Railway CLI, Docker, and `psql` are not.
- **DNS:** Cloudflare nameservers. `csetioko.me` has an A record pointing straight at `20.88.61.1` (DNS-only, not proxied).
- **Git:** local `main` (`4c40400`) is 3 docs-only commits ahead of what the VM pulled.

## Global Constraints

- The Railway web service deploys from the GitHub repo `owsetioko/career-platform`, branch `main`. Do not use any other repo or a CLI upload (`railway up`).
- The production domain is `csetioko.me`, with `www.csetioko.me` alongside it. The `*.up.railway.app` domain is only for checking the deploy before the DNS switch.
- Python `>=3.10` stays the floor in `pyproject.toml`; Railway runs 3.12 (pinned with `.python-version`).
- Dependencies are added to **both** `pyproject.toml` (then `uv lock`) **and** `requirements.txt`. The two files must keep listing the same runtime packages.
- Never print, log, commit, or pass a database URL on the command line. URLs are read from environment variables or `.env` only.
- Postgres integration tests run only when `TEST_DATABASE_URL` is set, and only against `localhost`/`127.0.0.1`. They must refuse any other host, because they drop tables.
- The SQLite path keeps working unchanged for local development and the existing test suite.
- Do not touch the Azure VM, its Nginx config, or its data during this plan. It is the rollback.
- Admin stays disabled on Railway (no `SESSION_SECRET` / `ADMIN_PASSWORD_HASH`), matching production today.

## Review Focus

1. **Railway hands the app `postgresql://` or `postgres://` URLs.** The app must connect with psycopg 3 for either scheme, not fail looking for psycopg2. Covered by Task 1.
2. **Static assets behind Railway's HTTPS proxy.** Page CSS and font URLs must come out as `https://`. Covered by Task 3's local proxy check and Task 4's live check.
3. **The pre-deploy step runs `initialize_database` on every deploy.** It must be idempotent on Postgres: no duplicate `owner` row and no failing `ALTER`. Covered by Task 2.
4. **The copy command run a second time, or pointed at a wrong source path.** It must refuse to overwrite a target that already has real content. A mistyped source path must not silently create an empty SQLite file and "copy" zero rows. Covered by Task 2.
5. **Admin inserts after the copy.** New rows must not collide with copied IDs, so Postgres sequences must be advanced past the copied maximums. Covered by Task 2.

---

## File Structure

| File | Change | Responsibility |
| --- | --- | --- |
| `app/database.py` | Modify | URL normalization to psycopg 3, `pool_pre_ping` for server databases, Postgres-safe boolean `ALTER` |
| `app/copy_database.py` | Create | One-shot `python -m app.copy_database <sqlite-path>` that copies all rows into the target URL |
| `tests/test_database.py` | Modify | Unit tests for URL normalization |
| `tests/test_copy_database.py` | Create | SQLite→SQLite copy tests (always run) |
| `tests/test_postgres.py` | Create | Postgres integration tests (run when `TEST_DATABASE_URL` is set) |
| `pyproject.toml`, `uv.lock`, `requirements.txt` | Modify | Add `psycopg[binary]` |
| `.python-version` | Create | Pin Python 3.12 for Railpack |
| `railway.json` | Create | Build/deploy config as code: pre-deploy, start command, health check |
| `.env.example` | Modify | Document `RAILWAY_DATABASE_URL` and `TEST_DATABASE_URL` |
| `README.md` | Modify | Railway deployment section |

---

### Task 1: Connect to Postgres with psycopg 3

**Files:**
- Modify: `app/database.py` (`get_database_url`/`create_database_engine` area)
- Modify: `pyproject.toml`, `uv.lock`, `requirements.txt`
- Test: `tests/test_database.py`

**Interfaces:**
- Produces: `normalize_database_url(database_url: str) -> str` in `app.database`. It rewrites driver `postgres` / `postgresql` to `postgresql+psycopg`, leaves every other URL (including an explicit `postgresql+psycopg2`) unchanged, and keeps the password intact. `create_database_engine` now applies it to every URL.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_database.py`; add `normalize_database_url` to the existing `from app.database import (...)` block)

```python
def test_railway_postgres_urls_use_psycopg_driver() -> None:
    assert (
        normalize_database_url("postgresql://user:pw@db.internal:5432/railway")
        == "postgresql+psycopg://user:pw@db.internal:5432/railway"
    )
    assert (
        normalize_database_url("postgres://user:pw@db.internal:5432/railway")
        == "postgresql+psycopg://user:pw@db.internal:5432/railway"
    )


def test_normalization_keeps_encoded_password_characters() -> None:
    assert (
        normalize_database_url("postgresql://user:p%40ss%2Fword@host/railway")
        == "postgresql+psycopg://user:p%40ss%2Fword@host/railway"
    )


def test_normalization_leaves_other_urls_alone() -> None:
    for url in (
        "sqlite:///:memory:",
        "sqlite:////tmp/resume.db",
        "postgresql+psycopg2://user:pw@host/railway",
    ):
        assert normalize_database_url(url) == url


def test_engine_for_railway_url_uses_psycopg() -> None:
    engine = create_database_engine("postgresql://user:pw@localhost:5432/railway")

    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg"
    engine.dispose()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_database.py -k "psycopg or normalization" -v`
Expected: FAIL with `ImportError: cannot import name 'normalize_database_url'`.

- [ ] **Step 3: Add the driver**

```bash
uv add "psycopg[binary]>=3.2,<4.0"
```

Then add the same line to `requirements.txt`, after `python-dotenv`:

```
psycopg[binary]>=3.2,<4.0
```

- [ ] **Step 4: Write the implementation** in `app/database.py`. Add this function directly above `get_database_url`, then replace the first line of `create_database_engine` and the `create_engine` call:

```python
def normalize_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg")
        return url.render_as_string(hide_password=False)
    return database_url
```

```python
def create_database_engine(database_url: str | None = None) -> Engine:
    url = make_url(normalize_database_url(database_url or get_database_url()))
    if (
        url.drivername.startswith("sqlite")
        and url.database not in (None, "", ":memory:")
    ):
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)

    if url.drivername.startswith("sqlite"):
        engine = create_engine(url)
    else:
        # Railway's proxy closes idle connections; check before reuse.
        engine = create_engine(url, pool_pre_ping=True)
    if url.drivername.startswith("sqlite"):
```

(The existing `@event.listens_for` block below stays as it is.)

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -q`
Expected: all tests pass, including the 4 new ones.

- [ ] **Step 6: Commit**

```bash
git add app/database.py tests/test_database.py pyproject.toml uv.lock requirements.txt
git commit -m "feat: connect to Railway Postgres through psycopg 3"
```

---

### Task 2: Postgres-safe schema setup and the SQLite → Postgres copy command

**Files:**
- Modify: `app/database.py` (`_add_missing_content_display_columns`)
- Create: `app/copy_database.py`
- Test: `tests/test_copy_database.py`, `tests/test_postgres.py`
- Modify: `.env.example`

**Interfaces:**
- Consumes: `normalize_database_url`, `create_database_engine`, `initialize_database`, `Base` from `app.database`.
- Produces:
  - `copy_database(source: Engine, target: Engine) -> dict[str, int]` returns rows copied per table name.
  - `TargetNotEmptyError(RuntimeError)`.
  - `main(argv: list[str] | None = None) -> int`, run as `uv run python -m app.copy_database data/resume.db [--target-env RAILWAY_DATABASE_URL]`.

- [ ] **Step 1: Install a local Postgres for integration tests**

```bash
brew install postgresql@17
brew services start postgresql@17
"$(brew --prefix postgresql@17)/bin/createdb" career_platform_test
```

Add to `.env.example`:

```
# One-time copy target: Railway Postgres public URL (Postgres service → Connect → Public Network).
# RAILWAY_DATABASE_URL=postgresql://...
# Optional: local Postgres for tests/test_postgres.py (localhost only; tests drop tables).
# TEST_DATABASE_URL=postgresql://localhost/career_platform_test
```

- [ ] **Step 2: Write the failing SQLite copy tests** in `tests/test_copy_database.py`

```python
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.copy_database import TargetNotEmptyError, copy_database, main
from app.database import (
    Experience,
    Profile,
    Skill,
    create_database_engine,
    initialize_database,
)


def _source_with_content(tmp_path):
    engine = initialize_database(
        create_database_engine(f"sqlite:///{tmp_path / 'source.db'}")
    )
    with Session(engine) as session, session.begin():
        owner = session.scalar(select(Profile).where(Profile.slug == "owner"))
        owner.display_name = "Chris Setioko"
        sql = Skill(name="SQL", is_visible=False, display_order=2)
        owner.skills.append(sql)
        owner.experiences.append(
            Experience(title="Operations Lead", company="Bakery", skills=[sql])
        )
    return engine


def test_copy_keeps_ids_links_and_flags_and_replaces_starter(tmp_path) -> None:
    source = _source_with_content(tmp_path)
    target = initialize_database(
        create_database_engine(f"sqlite:///{tmp_path / 'target.db'}")
    )

    counts = copy_database(source, target)

    assert counts["profiles"] == 1
    assert counts["experience_skills"] == 1
    with Session(target) as session:
        profiles = session.scalars(select(Profile)).all()
        assert [p.display_name for p in profiles] == ["Chris Setioko"]
        skill = session.scalar(select(Skill))
        assert (skill.name, skill.is_visible, skill.display_order) == ("SQL", False, 2)
        assert [s.name for s in session.scalar(select(Experience)).skills] == ["SQL"]


def test_copy_refuses_target_with_real_content(tmp_path) -> None:
    source = _source_with_content(tmp_path)
    target = _source_with_content(tmp_path / "other")

    with pytest.raises(TargetNotEmptyError):
        copy_database(source, target)

    with Session(target) as session:
        assert session.scalar(select(Profile)).display_name == "Chris Setioko"


def test_main_refuses_missing_source_file(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("COPY_TARGET", f"sqlite:///{tmp_path / 'target.db'}")
    missing = tmp_path / "typo.db"

    assert main([str(missing), "--target-env", "COPY_TARGET"]) == 2
    assert not missing.exists()
    assert "does not exist" in capsys.readouterr().err


def test_main_refuses_unset_target_without_echoing_urls(tmp_path, monkeypatch, capsys) -> None:
    _source_with_content(tmp_path)
    monkeypatch.delenv("COPY_TARGET", raising=False)

    assert main([str(tmp_path / "source.db"), "--target-env", "COPY_TARGET"]) == 2
    assert "COPY_TARGET is not set" in capsys.readouterr().err
```

`tmp_path / "other"` does not exist yet, so `create_database_engine` creates it (it already makes parent directories for SQLite files).

- [ ] **Step 3: Write the failing Postgres tests** in `tests/test_postgres.py`

```python
import os

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.copy_database import copy_database
from app.database import (
    Base,
    Profile,
    Skill,
    create_database_engine,
    initialize_database,
)

POSTGRES_URL = os.getenv("TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL, reason="set TEST_DATABASE_URL to run Postgres tests"
)


@pytest.fixture
def postgres_engine():
    host = make_url(POSTGRES_URL).host or "localhost"
    if host not in ("localhost", "127.0.0.1"):
        pytest.fail("TEST_DATABASE_URL must point at localhost; these tests drop tables")
    engine = create_database_engine(POSTGRES_URL)

    def reset() -> None:
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            for table in ("skills", "profiles"):
                connection.exec_driver_sql(f"DROP TABLE IF EXISTS {table} CASCADE")

    reset()
    yield engine
    reset()
    engine.dispose()


def test_initialization_is_idempotent_on_postgres(postgres_engine) -> None:
    initialize_database(postgres_engine)
    initialize_database(postgres_engine)

    with Session(postgres_engine) as session:
        assert len(session.scalars(select(Profile)).all()) == 1


def test_legacy_postgres_tables_gain_visible_by_default_columns(postgres_engine) -> None:
    with postgres_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE profiles (id SERIAL PRIMARY KEY, slug VARCHAR(80) NOT NULL UNIQUE, "
            "display_name VARCHAR(160) NOT NULL, headline VARCHAR(240) NOT NULL, "
            "summary VARCHAR(2000) NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE skills (id SERIAL PRIMARY KEY, profile_id INTEGER NOT NULL "
            "REFERENCES profiles (id) ON DELETE CASCADE, name VARCHAR(120) NOT NULL)"
        )

    initialize_database(postgres_engine)

    columns = {c["name"] for c in inspect(postgres_engine).get_columns("skills")}
    assert {"display_order", "is_visible"} <= columns
    with postgres_engine.begin() as connection:
        connection.execute(text("INSERT INTO skills (profile_id, name) VALUES (1, 'SQL')"))
        assert connection.scalar(text("SELECT is_visible FROM skills")) is True


def test_copy_into_postgres_advances_id_sequences(tmp_path, postgres_engine) -> None:
    source = initialize_database(
        create_database_engine(f"sqlite:///{tmp_path / 'source.db'}")
    )
    with Session(source) as session, session.begin():
        owner = session.scalar(select(Profile))
        owner.skills.extend([Skill(name="SQL"), Skill(name="Python")])
    initialize_database(postgres_engine)

    copy_database(source, postgres_engine)

    with Session(postgres_engine) as session, session.begin():
        owner = session.scalar(select(Profile))
        owner.skills.append(Skill(name="Tableau"))
    with Session(postgres_engine) as session:
        ids = sorted(session.scalars(select(Skill.id)).all())
        assert ids == [1, 2, 3]
```

- [ ] **Step 4: Run both test files to verify they fail**

Run: `TEST_DATABASE_URL=postgresql://localhost/career_platform_test uv run pytest tests/test_copy_database.py tests/test_postgres.py -v`
Expected: collection errors with `ModuleNotFoundError: No module named 'app.copy_database'`.

- [ ] **Step 5: Fix the boolean default** in `app/database.py`, `_add_missing_content_display_columns`:

```python
        "is_visible": "BOOLEAN NOT NULL DEFAULT TRUE",
```

(SQLite has accepted `TRUE` since 3.23, and stores it as `1`. The existing legacy-SQLite test keeps covering that path.)

- [ ] **Step 6: Write `app/copy_database.py`**

```python
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
```

- [ ] **Step 7: Run the new tests, then the full suite with and without Postgres**

Run: `TEST_DATABASE_URL=postgresql://localhost/career_platform_test uv run pytest -v`
Expected: all pass, including 4 copy tests and 3 Postgres tests.

Run: `uv run pytest -q`
Expected: all pass, with 3 skipped (Postgres tests).

- [ ] **Step 8: Rehearse the real copy locally**

```bash
"$(brew --prefix postgresql@17)/bin/createdb" career_platform_rehearsal
REHEARSAL_URL=postgresql://localhost/career_platform_rehearsal \
  uv run python -m app.copy_database data/resume.db --target-env REHEARSAL_URL
DATABASE_URL=postgresql://localhost/career_platform_rehearsal \
  uv run uvicorn app.main:app --port 8001 &
sleep 2; curl -s http://127.0.0.1:8001/ | grep -o "<title>[^<]*"; kill %1
```

Expected: printed counts `profiles: 1`, `skills: 15`, `experiences: 5`, `projects: 3`, `education: 3`, `project_tags: 0`, `experience_skills: 8`, `project_skills: 4`, and the real name in `<title>`. Run the copy command again and expect exit 1 with "already has resume content".

- [ ] **Step 9: Commit**

```bash
git add app/database.py app/copy_database.py tests/test_copy_database.py tests/test_postgres.py .env.example
git commit -m "feat: add SQLite-to-Postgres copy command and Postgres-safe schema setup"
```

---

### Task 3: Railway build and deploy config

**Files:**
- Create: `railway.json`, `.python-version`
- Modify: `README.md` (new section above "Future Azure Linux VM readiness")

**Interfaces:**
- Consumes: `python -m app.database` (existing `initialize_database` entry point), `app.main:app`.
- Produces: config that Task 4's Railway deploy reads from the repo.

- [ ] **Step 1: Show the mixed-content bug locally** (the failing check)

By default, Uvicorn trusts proxy headers only from `127.0.0.1`, so a plain local `curl` hides the bug. Railway's proxy connects from a non-loopback address. To simulate that, trust some other address:

```bash
uv run uvicorn app.main:app --port 8002 --forwarded-allow-ips=192.0.2.1 &
sleep 2
curl -s -H "X-Forwarded-Proto: https" -H "Host: csetioko.me" http://127.0.0.1:8002/ | grep -o 'href="[^"]*styles.css'
kill %1
```

Expected: `href="http://csetioko.me/static/css/styles.css"`. That is an `http://` URL on an HTTPS page, which the browser blocks.

- [ ] **Step 2: Create `.python-version`**

```
3.12
```

- [ ] **Step 3: Create `railway.json`**

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "RAILPACK"
  },
  "deploy": {
    "preDeployCommand": ["python -m app.database"],
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*",
    "healthcheckPath": "/",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

Use one worker: the site is a single read-mostly page, and Railway bills by memory. `--forwarded-allow-ips=*` is safe here because only Railway's edge can reach the container's port.

- [ ] **Step 4: Verify the fix locally with the same flags**

```bash
PORT=8002 sh -c 'uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips=*' &
sleep 2
curl -s -H "X-Forwarded-Proto: https" -H "Host: csetioko.me" http://127.0.0.1:8002/ | grep -o 'href="[^"]*styles.css'
kill %1
```

Expected: `href="https://csetioko.me/static/css/styles.css"`.

- [ ] **Step 5: Add a README section** directly above `## Future Azure Linux VM readiness (guidance only)`:

```markdown
## Deploy on Railway

Production runs on Railway: one web service built from this repository, plus
a PostgreSQL service in the same project. `railway.json` holds the deploy
settings:

- Railpack installs dependencies from `uv.lock` and uses Python from `.python-version`.
- Before each deploy goes live, `python -m app.database` creates any missing
  tables and the starter `owner` row. It is safe to run on every deploy.
- Uvicorn trusts Railway's proxy headers, so static URLs are built as `https://`.

The web service needs these variables:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference to the Postgres service's private URL) |
| `APP_TITLE` | `Personal Resume Platform` |

`SESSION_SECRET`, `ADMIN_PASSWORD_HASH`, and `SESSION_COOKIE_SECURE=true` are
needed only to turn on the owner admin (see "Configure the owner admin").

To load resume content from a local SQLite file into an empty Railway
database, put the Postgres service's public URL in `.env` as
`RAILWAY_DATABASE_URL`, then run:

    uv run python -m app.copy_database data/resume.db

It keeps row IDs, resets ID sequences, and refuses to run if the target
already holds resume content.

The page snapshot in `data/public-profile.json` lives on the container's
disk and is rebuilt after each deploy on the first successful page load.
```

- [ ] **Step 6: Run the suite and commit**

Run: `uv run pytest -q`
Expected: all pass (Postgres tests skipped).

```bash
git add railway.json .python-version README.md
git commit -m "feat: add Railway deploy config"
```

---

### Task 4: Configure, load, and deploy on Railway (operational, on Railway's default domain)

**Where:** `LAPTOP` (Railway CLI + `uv`) and `RAILWAY` (railway.com dashboard). No code changes; this task ends when the site works at `https://<service>.up.railway.app`.

- [ ] **Step 1: Install and link the CLI**

```bash
brew install railway
railway login
railway link        # pick the existing project, then the web service
railway status
```

Expected: `railway status` names the project, the `production` environment, and the web service.

- [ ] **Step 2: Find the Postgres service's name** in the dashboard (Project canvas). The reference below assumes it is `Postgres`; if the canvas shows another name, use that name inside `${{…}}`.

- [ ] **Step 3: Set the web service's variables** (`railway variables --set` writes to the linked service)

```bash
railway variables --set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' \
                  --set 'APP_TITLE=Personal Resume Platform'
railway variables --kv | sed 's/=.*/=<set>/'
```

Expected: `DATABASE_URL=<set>` and `APP_TITLE=<set>` (values hidden on purpose).

- [ ] **Step 4: Push the branch and connect the repo**

```bash
git push origin main
```

In the dashboard, open the web service and go to Settings → Source. Confirm it is connected to `owsetioko/career-platform`, branch `main`. If it is connected to anything else, or to nothing, disconnect it and connect `owsetioko/career-platform` / `main`. Deploys come only from this repo, never from `railway up`. Confirm Settings → Config-as-code picks up `railway.json` (the pre-deploy and start commands appear greyed out with "from railway.json").

- [ ] **Step 5: Load the data.** This is safe before or after the first deploy. If the pre-deploy step already created the starter `owner` row, the copy replaces it. Nothing is public yet: `csetioko.me` still points at the VM. Confirm the VM copy still matches the laptop copy, then run the copy:

```bash
ssh -i ~/.ssh/isba4775_azure azureuser@20.88.61.1 'sqlite3 ~/career-platform/data/resume.db .dump | shasum'
sqlite3 data/resume.db .dump | shasum
uv run python -m app.copy_database data/resume.db
```

Expected: identical hashes (the 2026-10-08 value was `8989f2cf03bf4684bc5e24390b6ef9781bb48ff8`), then the same counts as the Task 2 rehearsal. If the hashes differ, `scp` the VM's file down first and copy from that.

- [ ] **Step 6: Deploy and watch**

Trigger a deploy (Deployments → Deploy, or push). In the logs, check for:
- build: Railpack detects Python 3.12 and `uv.lock`, and installs `psycopg`;
- pre-deploy: `python -m app.database` exits 0;
- deploy: `Uvicorn running on http://0.0.0.0:<port>` and the health check passes.

- [ ] **Step 7: Generate the Railway domain and verify the live page**

Settings → Networking → Generate Domain. Then:

```bash
URL=https://<generated>.up.railway.app
curl -s "$URL/" | grep -o "<title>[^<]*"
curl -s "$URL/" | grep -o 'href="[^"]*styles.css'
curl -s -o /dev/null -w "%{http_code}\n" "$URL/static/css/styles.css"
curl -s -o /dev/null -w "%{http_code}\n" "$URL/admin"
```

Expected: the real name in `<title>`; `href="https://<generated>.up.railway.app/static/css/styles.css"`; `200` for the CSS. `/admin` should behave as it does on the VM today (admin not configured). Open the URL in Chrome and compare it side by side with `https://csetioko.me`: same content, fonts, and layout, with no console errors.

---

### Task 5: Move `csetioko.me` to Railway (operational)

**Where:** `RAILWAY` dashboard, `CLOUDFLARE` dashboard, `LAPTOP`.

- [ ] **Step 1: Lower the TTL a day ahead.** In Cloudflare DNS, set the TTL on the `csetioko.me` and `www` records to 5 minutes, so a rollback propagates quickly.

- [ ] **Step 2: Add the custom domains in Railway.** In the web service, go to Settings → Networking → Custom Domain and add `csetioko.me`, then `www.csetioko.me`. Railway shows a CNAME target and a `_railway-verify` TXT record for each.

- [ ] **Step 3: Update Cloudflare DNS** (keep both records **DNS only**, grey cloud, so Railway can issue its certificate):
  - Add each `_railway-verify…` TXT record exactly as Railway shows it.
  - Replace the `csetioko.me` A record (`20.88.61.1`) with a CNAME to the Railway target. Cloudflare flattens a CNAME at the apex automatically.
  - Point `www` at its Railway CNAME target.

- [ ] **Step 4: Verify**

```bash
dig +short csetioko.me
openssl s_client -connect csetioko.me:443 -servername csetioko.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
curl -s https://csetioko.me/ | grep -o "<title>[^<]*"
curl -s -o /dev/null -w "%{http_code}\n" https://www.csetioko.me/
```

Expected: Railway IPs (not `20.88.61.1`), a valid, newly issued certificate for `csetioko.me` (Railway issues and renews it), the real name in the title, and `200` from `www`. Both domains show "Active" in Railway.

- [ ] **Step 5: Rollback path (only if Step 4 fails and can't be fixed quickly).** Put the A record for `csetioko.me` back to `20.88.61.1` (DNS only) and point `www` back to the VM the same way. The VM's Nginx and Let's Encrypt setup is unchanged and still serves the site.

- [ ] **Step 6: Leave the VM running for 7 days**, then decide on decommissioning separately (stop/deallocate first; keep a final `scp` of `data/resume.db`). This plan does not delete any Azure resource.

- [ ] **Step 7: Flag the outdated write-up to Chris.** `docs/how-this-site-is-secured.md` is Chris's own description of the VM setup: Let's Encrypt + Certbot, the Azure NSG ports, and encryption ending at Nginx. It will no longer be accurate. Leave it unedited and tell Chris which sections changed. Railway now issues and renews the certificate, and TLS ends at Railway's edge. There are no open ports to manage. The `openssl` output will show the new issuer.
