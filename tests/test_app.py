from datetime import date

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.database import (
    Base,
    Education,
    Experience,
    Profile,
    Project,
    ProjectTag,
    Skill,
    create_database_engine,
)
from app.main import app


def _create_profile_database(database_url: str, profile: Profile) -> None:
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(profile)
        session.commit()
    engine.dispose()


def test_public_profile_renders_persisted_content_in_recruiter_friendly_order(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile.db'}"
    sql_skill = Skill(name="SQL")
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="Turns complex data into useful insights.",
            skills=[sql_skill],
            experiences=[
                Experience(
                    title="Data Analyst",
                    company="Example Organization",
                    location="Remote",
                    description="Built reporting workflows.",
                    start_date=date(2023, 1, 1),
                    end_date=date(2025, 6, 1),
                    skills=[sql_skill],
                )
            ],
            projects=[
                Project(
                    name="Sales Insights",
                    description="Analyzed sales trends.",
                    url="https://example.com/project",
                    skills=[sql_skill],
                    tags=[ProjectTag(name="Analytics")],
                )
            ],
            education=[
                Education(
                    institution="Example University",
                    degree="Bachelor of Science",
                    field_of_study="Analytics",
                )
            ],
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Jordan Lee" in response.text
    assert "Data Analyst" in response.text
    assert "Turns complex data into useful insights." in response.text
    assert "Example Organization" in response.text
    assert "SQL" in response.text
    assert "Sales Insights" in response.text
    assert "Analytics" in response.text
    assert "Example University" in response.text
    assert "https://example.com/project" in response.text
    assert "<main" in response.text
    assert response.text.index("Experience") < response.text.index("Skills")
    assert response.text.index("Skills") < response.text.index("Projects")
    assert response.text.index("Projects") < response.text.index("Education")
    assert "<title>Jordan Lee | Data Analyst</title>" in response.text
    assert 'name="description"' in response.text
    assert 'content="Turns complex data into useful insights."' in response.text


def test_public_profile_shows_empty_states_and_omits_missing_optional_values(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty-profile.db'}"
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="",
            experiences=[
                Experience(
                    title="Analyst",
                    company="Example Organization",
                    start_date=date(2023, 1, 1),
                )
            ],
            projects=[Project(name="Internal project")],
            education=[
                Education(
                    institution="Example University",
                    start_date=date(2022, 1, 1),
                )
            ],
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "No professional summary provided." in response.text
    assert "No skills listed yet." in response.text
    assert "Present" not in response.text
    assert "No location available." not in response.text
    assert "No experience description available." not in response.text
    assert "No project description available." not in response.text
    assert "No education details available." not in response.text
    assert "mailto:" not in response.text
    assert "linkedin.com" not in response.text


def test_public_profile_shows_empty_states_for_unpopulated_sections(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile-without-sections.db'}"
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="",
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "No experience listed yet." in response.text
    assert "No skills listed yet." in response.text
    assert "No projects listed yet." in response.text
    assert "No education listed yet." in response.text


def test_public_profile_shows_only_configured_contact_links(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile-with-contact.db'}"
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="",
            email="jordan@example.com",
            website="https://jordan.example.com",
            linkedin_url="https://www.linkedin.com/in/jordan-lee",
            github_url="https://github.com/jordan-lee",
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert (
        '<section class="profile-section contact-section" id="contact"'
        in response.text
    )
    assert 'aria-labelledby="contact-heading"' in response.text
    assert "<h2 id=\"contact-heading\">Contact</h2>" in response.text
    assert '<a href="mailto:jordan@example.com">Email</a>' in response.text
    assert '<a href="https://jordan.example.com">Website</a>' in response.text
    assert (
        '<a href="https://www.linkedin.com/in/jordan-lee">LinkedIn</a>'
        in response.text
    )
    assert '<a href="https://github.com/jordan-lee">GitHub</a>' in response.text


def test_public_profile_omits_unconfigured_contact_links(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile-partial-contact.db'}"
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="",
            email="jordan@example.com",
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert '<a href="mailto:jordan@example.com">Email</a>' in response.text
    assert "Website" not in response.text
    assert "LinkedIn" not in response.text
    assert "GitHub" not in response.text


def test_public_profile_shows_truthful_empty_contact_state(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile-without-contact.db'}"
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="",
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert (
        '<section class="profile-section contact-section" id="contact"'
        in response.text
    )
    assert "<h2 id=\"contact-heading\">Contact</h2>" in response.text
    assert "No contact methods have been provided." in response.text
    assert "mailto:" not in response.text
    assert "linkedin.com" not in response.text


def test_profile_stylesheet_is_served_with_mobile_responsive_rules() -> None:
    response = TestClient(app).get("/static/css/styles.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "@media" in response.text
    assert "max-width" in response.text
