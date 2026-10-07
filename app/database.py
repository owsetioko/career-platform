from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
    URL,
    create_engine,
    event,
    inspect,
    select,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

APP_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(APP_ROOT / ".env")


class Base(DeclarativeBase):
    pass


experience_skills = Table(
    "experience_skills",
    Base.metadata,
    Column(
        "experience_id",
        ForeignKey("experiences.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "skill_id",
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

project_skills = Table(
    "project_skills",
    Base.metadata,
    Column(
        "project_id",
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "skill_id",
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    headline: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(String(2000))
    email: Mapped[str | None] = mapped_column(String(320), default=None)
    website: Mapped[str | None] = mapped_column(String(1000), default=None)
    linkedin_url: Mapped[str | None] = mapped_column(String(1000), default=None)
    github_url: Mapped[str | None] = mapped_column(String(1000), default=None)

    experiences: Mapped[list[Experience]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by=lambda: (Experience.display_order, Experience.id),
    )
    skills: Mapped[list[Skill]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by=lambda: (Skill.display_order, Skill.id),
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by=lambda: (Project.display_order, Project.id),
    )
    education: Mapped[list[Education]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by=lambda: (Education.display_order, Education.id),
    )


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("profile_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    display_order: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    profile: Mapped[Profile] = relationship(back_populates="skills")
    experiences: Mapped[list[Experience]] = relationship(
        secondary=experience_skills, back_populates="skills"
    )
    projects: Mapped[list[Project]] = relationship(
        secondary=project_skills, back_populates="skills"
    )


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200), default=None)
    description: Mapped[str | None] = mapped_column(String(4000), default=None)
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    display_order: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    profile: Mapped[Profile] = relationship(back_populates="experiences")
    skills: Mapped[list[Skill]] = relationship(
        secondary=experience_skills, back_populates="experiences"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(4000), default=None)
    url: Mapped[str | None] = mapped_column(String(1000), default=None)
    display_order: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    profile: Mapped[Profile] = relationship(back_populates="projects")
    skills: Mapped[list[Skill]] = relationship(
        secondary=project_skills, back_populates="projects"
    )
    tags: Mapped[list[ProjectTag]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectTag(Base):
    __tablename__ = "project_tags"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))

    project: Mapped[Project] = relationship(back_populates="tags")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )
    institution: Mapped[str] = mapped_column(String(200))
    degree: Mapped[str | None] = mapped_column(String(200), default=None)
    field_of_study: Mapped[str | None] = mapped_column(String(200), default=None)
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    description: Mapped[str | None] = mapped_column(String(4000), default=None)
    display_order: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    profile: Mapped[Profile] = relationship(back_populates="education")


def get_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    return URL.create(
        "sqlite", database=str(APP_ROOT / "data" / "resume.db")
    ).render_as_string(hide_password=False)


def create_database_engine(database_url: str | None = None) -> Engine:
    url = make_url(database_url or get_database_url())
    if (
        url.drivername.startswith("sqlite")
        and url.database not in (None, "", ":memory:")
    ):
        Path(url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url)
    if url.drivername.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def _add_missing_profile_contact_columns(engine: Engine) -> None:
    if not inspect(engine).has_table("profiles"):
        return

    existing_columns = {
        column["name"] for column in inspect(engine).get_columns("profiles")
    }
    contact_columns = {
        "email": "VARCHAR(320)",
        "website": "VARCHAR(1000)",
        "linkedin_url": "VARCHAR(1000)",
        "github_url": "VARCHAR(1000)",
    }
    with engine.begin() as connection:
        for name, column_type in contact_columns.items():
            if name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE profiles ADD COLUMN {name} {column_type}"
                )


def _add_missing_content_display_columns(engine: Engine) -> None:
    display_columns = {
        "display_order": "INTEGER NOT NULL DEFAULT 0",
        "is_visible": "BOOLEAN NOT NULL DEFAULT 1",
    }
    for table in ("experiences", "skills", "projects", "education"):
        if not inspect(engine).has_table(table):
            continue
        existing_columns = {
            column["name"] for column in inspect(engine).get_columns(table)
        }
        with engine.begin() as connection:
            for name, column_type in display_columns.items():
                if name not in existing_columns:
                    connection.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"
                    )


def initialize_database(engine: Engine | None = None) -> Engine:
    database_engine = engine or create_database_engine()
    Base.metadata.create_all(database_engine)
    _add_missing_profile_contact_columns(database_engine)
    _add_missing_content_display_columns(database_engine)

    with Session(database_engine) as session, session.begin():
        starter_profile = session.scalar(
            select(Profile).where(Profile.slug == "owner")
        )
        if starter_profile is None:
            session.add(
                Profile(
                    slug="owner",
                    display_name="Your Name",
                    headline="Business Analytics Senior",
                    summary="Add a short professional summary.",
                )
            )

    return database_engine


if __name__ == "__main__":
    initialize_database()
