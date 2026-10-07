import json
import logging
from datetime import date

import pytest
from sqlalchemy.exc import OperationalError
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
from app.main import app, get_session


@pytest.fixture(autouse=True)
def isolate_profile_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.PROFILE_CACHE_PATH", tmp_path / "public-profile.json"
    )


def _install_unavailable_database(monkeypatch) -> None:
    class UnavailableSession:
        def scalar(self, _statement):
            raise OperationalError(
                "SELECT profile", {}, RuntimeError("database is unavailable")
            )

    def unavailable_session():
        yield UnavailableSession()

    monkeypatch.setitem(app.dependency_overrides, get_session, unavailable_session)


def _cached_profile(display_name: str) -> dict:
    return {
        "slug": "owner",
        "display_name": display_name,
        "headline": "Business Analytics Senior",
        "summary": "Add a short professional summary.",
        "email": None,
        "website": None,
        "linkedin_url": None,
        "github_url": None,
        "experiences": [],
        "skills": [],
        "projects": [],
        "education": [],
    }


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


def test_public_profile_renders_profile_skills_in_configured_order(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'ordered-profile-skills.db'}"
    alpha_skill = Skill(name="Alpha", display_order=2)
    beta_skill = Skill(name="Beta", display_order=0)
    zulu_skill = Skill(name="Zulu", display_order=1)
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Jordan Lee",
            headline="Data Analyst",
            summary="",
            skills=[alpha_skill, beta_skill, zulu_skill],
            experiences=[
                Experience(
                    title="Data Analyst",
                    company="Example Organization",
                    skills=[alpha_skill, beta_skill, zulu_skill],
                )
            ],
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    profile_skills = response.text.split(
        '<section class="profile-section" id="skills"', 1
    )[1].split("</section>", 1)[0]
    assert profile_skills.index("Beta") < profile_skills.index("Zulu")
    assert profile_skills.index("Zulu") < profile_skills.index("Alpha")

    experience_section = response.text.split(
        '<section class="profile-section" id="experience"', 1
    )[1].split('<section class="profile-section"', 1)[0]
    assert experience_section.index("Beta") < experience_section.index("Zulu")
    assert experience_section.index("Zulu") < experience_section.index("Alpha")


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


def test_first_database_outage_renders_bundled_truthful_fallback(
    tmp_path, monkeypatch, caplog
) -> None:
    monkeypatch.setattr(
        "app.main.PROFILE_CACHE_PATH", tmp_path / "profile-cache.json", raising=False
    )
    _install_unavailable_database(monkeypatch)

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Business Analytics Senior" in response.text
    assert "Your Name" in response.text
    assert "Add a short professional summary." in response.text
    assert "profile data is temporarily unavailable" in response.text
    assert "Traceback" not in response.text
    assert "Public profile database read failed" in caplog.text
    assert not (tmp_path / "profile-cache.json").exists()


def test_database_outage_renders_last_known_good_cache(tmp_path, monkeypatch) -> None:
    cache_path = tmp_path / "profile-cache.json"
    cache_path.write_text(json.dumps(_cached_profile("Saved Profile")), encoding="utf-8")
    monkeypatch.setattr("app.main.PROFILE_CACHE_PATH", cache_path, raising=False)
    _install_unavailable_database(monkeypatch)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Saved Profile" in response.text
    assert "Business Analytics Senior" in response.text
    assert "profile data is temporarily unavailable" in response.text


def test_live_profile_refreshes_cache_and_cached_copy_survives_outage(
    tmp_path, monkeypatch
) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile.db'}"
    cache_path = tmp_path / "data" / "profile-cache.json"
    monkeypatch.setattr("app.main.PROFILE_CACHE_PATH", cache_path, raising=False)
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Live Profile",
            headline="Business Analytics Senior",
            summary="Live profile summary.",
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    live_response = TestClient(app).get("/")

    assert live_response.status_code == 200
    assert "Live Profile" in live_response.text
    snapshot = json.loads(cache_path.read_text(encoding="utf-8"))
    assert snapshot["display_name"] == "Live Profile"
    assert snapshot["summary"] == "Live profile summary."

    _install_unavailable_database(monkeypatch)
    outage_response = TestClient(app).get("/")

    assert outage_response.status_code == 200
    assert "Live Profile" in outage_response.text
    assert "Live profile summary." in outage_response.text


def test_cache_write_failure_does_not_break_live_rendering(
    tmp_path, monkeypatch, caplog
) -> None:
    database_url = f"sqlite:///{tmp_path / 'profile.db'}"
    monkeypatch.setattr("app.main.PROFILE_CACHE_PATH", tmp_path, raising=False)
    _create_profile_database(
        database_url,
        Profile(
            slug="owner",
            display_name="Live Profile",
            headline="Business Analytics Senior",
            summary="Live profile summary.",
        ),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Live Profile" in response.text
    assert "Could not refresh public profile cache" in caplog.text


def test_missing_profile_is_not_replaced_by_cached_fallback(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty.db'}"
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setattr(
        "app.main.PROFILE_CACHE_PATH", tmp_path / "profile-cache.json", raising=False
    )
    (tmp_path / "profile-cache.json").write_text(
        json.dumps(_cached_profile("Must Not Render")), encoding="utf-8"
    )

    response = TestClient(app).get("/")

    assert response.status_code == 404
    assert "Must Not Render" not in response.text


def test_unreadable_bundled_fallback_surfaces_explicit_error(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.main.PROFILE_CACHE_PATH", tmp_path / "missing-cache.json", raising=False
    )
    invalid_fallback = tmp_path / "invalid-fallback.json"
    invalid_fallback.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(
        "app.main.BUNDLED_FALLBACK_PATH", invalid_fallback, raising=False
    )
    _install_unavailable_database(monkeypatch)

    response = TestClient(app, raise_server_exceptions=False).get("/")

    assert response.status_code == 500
    assert "Profile fallback is unavailable" in response.text


@pytest.mark.parametrize(
    "bad_snapshot",
    ["{not valid json", json.dumps({"display_name": "Missing required fields"})],
)
def test_unusable_cache_uses_bundled_fallback(
    tmp_path, monkeypatch, bad_snapshot
) -> None:
    cache_path = tmp_path / "profile-cache.json"
    cache_path.write_text(bad_snapshot, encoding="utf-8")
    monkeypatch.setattr("app.main.PROFILE_CACHE_PATH", cache_path, raising=False)
    _install_unavailable_database(monkeypatch)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Business Analytics Senior" in response.text
    assert "profile data is temporarily unavailable" in response.text
