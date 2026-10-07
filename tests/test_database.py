from datetime import date

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.database import (
    Education,
    Experience,
    Profile,
    Project,
    ProjectTag,
    Skill,
    create_database_engine,
    get_database_url,
    initialize_database,
)


def test_initialization_creates_content_tables_and_editable_starter_profile() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    initialize_database(engine)

    assert {
        "profiles",
        "experiences",
        "skills",
        "projects",
        "project_tags",
        "education",
        "experience_skills",
        "project_skills",
    }.issubset(set(inspect(engine).get_table_names()))
    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.slug == "owner"))

    assert profile is not None
    assert profile.display_name == "Your Name"
    assert profile.headline == "Business Analytics Senior"
    assert profile.summary == "Add a short professional summary."
    engine.dispose()


def test_initialization_does_not_duplicate_the_starter_profile() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    initialize_database(engine)
    initialize_database(engine)

    with Session(engine) as session:
        profiles = session.scalars(
            select(Profile).where(Profile.slug == "owner")
        ).all()

    assert len(profiles) == 1
    engine.dispose()


def test_profile_content_and_skill_and_tag_relationships_round_trip() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    initialize_database(engine)

    with Session(engine) as session:
        profile = Profile(
            slug="example",
            display_name="Example Person",
            headline="Analytics Example",
            summary="Example profile summary.",
        )
        skill = Skill(name="SQL", profile=profile)
        profile.experiences.append(
            Experience(
                title="Analyst",
                company="Example Company",
                description="Example experience.",
                start_date=date(2024, 1, 1),
                skills=[skill],
            )
        )
        profile.projects.append(
            Project(
                name="Example project",
                description="Example project description.",
                skills=[skill],
                tags=[ProjectTag(name="analytics"), ProjectTag(name="portfolio")],
            )
        )
        profile.education.append(
            Education(
                institution="Example University",
                degree="Bachelor's",
                field_of_study="Business Analytics",
            )
        )
        session.add(profile)
        session.commit()
        session.expire_all()

        loaded_profile = session.scalar(
            select(Profile).where(Profile.slug == "example")
        )

        assert loaded_profile is not None
        assert [item.title for item in loaded_profile.experiences] == ["Analyst"]
        assert [item.name for item in loaded_profile.experiences[0].skills] == [
            "SQL"
        ]
        assert [item.name for item in loaded_profile.projects[0].skills] == ["SQL"]
        assert {tag.name for tag in loaded_profile.projects[0].tags} == {
            "analytics",
            "portfolio",
        }
        assert loaded_profile.education[0].institution == "Example University"
        assert loaded_profile.experiences[0].start_date == date(2024, 1, 1)
    engine.dispose()


def test_profile_contact_fields_round_trip() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    initialize_database(engine)

    with Session(engine) as session:
        profile = Profile(
            slug="contact-example",
            display_name="Example Person",
            headline="Analytics Example",
            summary="Example profile summary.",
            email="person@example.com",
            website="https://example.com",
            linkedin_url="https://www.linkedin.com/in/example",
            github_url="https://github.com/example",
        )
        session.add(profile)
        session.commit()
        session.expire_all()

        loaded_profile = session.scalar(
            select(Profile).where(Profile.slug == "contact-example")
        )

        assert loaded_profile is not None
        assert loaded_profile.email == "person@example.com"
        assert loaded_profile.website == "https://example.com"
        assert loaded_profile.linkedin_url == "https://www.linkedin.com/in/example"
        assert loaded_profile.github_url == "https://github.com/example"
    engine.dispose()


def test_initialization_adds_contact_fields_to_existing_sqlite_profile(
    tmp_path,
) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'legacy-profile.db'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE profiles ("
                "id INTEGER PRIMARY KEY, "
                "slug VARCHAR(80) NOT NULL UNIQUE, "
                "display_name VARCHAR(160) NOT NULL, "
                "headline VARCHAR(240) NOT NULL, "
                "summary VARCHAR(2000) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO profiles (slug, display_name, headline, summary) "
                "VALUES ('owner', 'Example Person', 'Analytics Example', "
                "'Example profile summary.')"
            )
        )

    initialize_database(engine)

    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.slug == "owner"))

        assert profile is not None
        assert profile.email is None
        assert profile.website is None
        assert profile.linkedin_url is None
        assert profile.github_url is None
        profile.email = "person@example.com"
        session.commit()
        session.expire_all()

        reloaded_profile = session.scalar(
            select(Profile).where(Profile.slug == "owner")
        )

        assert reloaded_profile is not None
        assert reloaded_profile.email == "person@example.com"
    engine.dispose()


def test_database_url_uses_configured_environment_value(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    assert get_database_url() == "sqlite:///:memory:"


def test_database_url_defaults_under_project_data_directory(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url().endswith("/data/resume.db")
