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
