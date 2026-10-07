from __future__ import annotations

import re
from datetime import date

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import (
    Education,
    Experience,
    Profile,
    Project,
    ProjectTag,
    Skill,
    create_database_engine,
    initialize_database,
)
from app import main

PASSWORD = "safe-test-password"


def _csrf_token(response) -> str:
    match = re.search(
        r'<input[^>]+name="csrf_token"[^>]+value="([^"]+)"', response.text
    )
    assert match is not None, "form did not include a CSRF token"
    return match.group(1)


def _client(
    tmp_path, monkeypatch, *, configured: bool = True, secure_cookie: bool = False
):
    database_url = f"sqlite:///{tmp_path / 'admin.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", str(secure_cookie).lower())
    if configured:
        monkeypatch.setenv(
            "ADMIN_PASSWORD_HASH", PasswordHasher().hash(PASSWORD)
        )
        monkeypatch.setenv("SESSION_SECRET", "test-only-session-secret-" + "x" * 40)

    initialize_database(create_database_engine(database_url))
    assert callable(getattr(main, "create_app", None)), "admin app factory is missing"
    return (
        TestClient(
            main.create_app(),
            follow_redirects=False,
            base_url="https://testserver" if secure_cookie else "http://testserver",
        ),
        database_url,
    )


def _login(client: TestClient) -> TestClient:
    response = client.get("/admin/login")
    token = _csrf_token(response)
    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "password": PASSWORD},
    )
    assert response.status_code == 303
    return client


def test_admin_is_explicitly_disabled_without_credentials_but_public_still_works(
    tmp_path, monkeypatch
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch, configured=False)

    response = client.get("/admin/login")
    public_response = client.get("/")

    assert response.status_code == 503
    assert "Admin is not configured" in response.text
    assert public_response.status_code == 200
    assert "Your Name" in public_response.text


@pytest.mark.parametrize("missing_setting", ["ADMIN_PASSWORD_HASH", "SESSION_SECRET"])
def test_admin_is_disabled_when_either_required_secret_is_missing(
    tmp_path, monkeypatch, missing_setting
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch)
    monkeypatch.delenv(missing_setting)

    response = TestClient(main.create_app()).get("/admin")

    assert response.status_code == 503
    assert "Admin is not configured" in response.text


def test_admin_is_disabled_when_password_hash_is_not_valid_argon2id(
    tmp_path, monkeypatch
) -> None:
    _client(tmp_path, monkeypatch)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "$argon2id$not-a-valid-hash")

    response = TestClient(main.create_app()).get("/admin/login")

    assert response.status_code == 503
    assert "Admin is not configured" in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/profile",
        "/admin/experiences",
        "/admin/skills",
        "/admin/projects",
        "/admin/education",
        "/admin/experiences/new",
    ],
)
def test_admin_pages_redirect_unauthenticated_visitors_to_login(
    tmp_path, monkeypatch, path: str
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch)

    response = client.get(path)
    blocked_write = client.post("/admin/profile", data={"display_name": "Nope"})

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"
    assert blocked_write.status_code == 303
    assert blocked_write.headers["location"] == "/admin/login"


def test_tampered_signed_session_cookie_does_not_authenticate(
    tmp_path, monkeypatch
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch)
    client.cookies.set("resume_session", "authenticated=true")

    response = client.get("/admin")

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_login_rejects_invalid_password_and_accepts_argon2_password(
    tmp_path, monkeypatch
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch)
    login_page = client.get("/admin/login")
    token = _csrf_token(login_page)

    invalid = client.post(
        "/admin/login",
        data={"csrf_token": token, "password": "wrong-password"},
    )
    dashboard = client.get("/admin")

    assert invalid.status_code == 401
    assert "Invalid password" in invalid.text
    assert dashboard.status_code == 303

    token = _csrf_token(client.get("/admin/login"))
    accepted = client.post(
        "/admin/login",
        data={"csrf_token": token, "password": PASSWORD},
    )

    assert accepted.status_code == 303
    assert accepted.headers["location"] == "/admin"
    cookie = accepted.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_login_and_content_changes_reject_missing_or_forged_csrf_tokens(
    tmp_path, monkeypatch
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch)
    login_page = client.get("/admin/login")

    missing_login_token = client.post(
        "/admin/login", data={"password": PASSWORD}
    )

    assert missing_login_token.status_code == 403
    _login(client)
    rejected_write = client.post(
        "/admin/profile",
        data={
            "csrf_token": "forged",
            "display_name": "Attacker",
            "headline": "Bad",
            "summary": "Bad",
        },
    )

    assert rejected_write.status_code == 403
    assert _csrf_token(login_page)


def test_session_cookie_secure_flag_can_be_enabled(tmp_path, monkeypatch) -> None:
    client, _database_url = _client(tmp_path, monkeypatch, secure_cookie=True)
    token = _csrf_token(client.get("/admin/login"))

    response = client.post(
        "/admin/login",
        data={"csrf_token": token, "password": PASSWORD},
    )

    assert response.status_code == 303
    assert "secure" in response.headers["set-cookie"].lower()


def test_logout_requires_csrf_and_clears_authenticated_session(
    tmp_path, monkeypatch
) -> None:
    client, _database_url = _client(tmp_path, monkeypatch)
    _login(client)

    rejected = client.post("/admin/logout", data={"csrf_token": "forged"})
    logout_page = client.get("/admin")
    token = _csrf_token(logout_page)
    accepted = client.post("/admin/logout", data={"csrf_token": token})
    dashboard = client.get("/admin")

    assert rejected.status_code == 403
    assert accepted.status_code == 303
    assert dashboard.status_code == 303


@pytest.mark.parametrize(
    ("kind", "form", "model", "display_field", "display_value"),
    [
        (
            "experiences",
            {
                "title": "Analyst",
                "company": "Example Co",
                "location": "Remote",
                "description": "Built reporting.",
                "start_date": "2024-01-01",
                "end_date": "2025-01-01",
            },
            Experience,
            "title",
            "Analyst",
        ),
        (
            "skills",
            {"name": "Python"},
            Skill,
            "name",
            "Python",
        ),
        (
            "projects",
            {
                "name": "Insights",
                "description": "A useful project.",
                "url": "https://example.com/project",
            },
            Project,
            "name",
            "Insights",
        ),
        (
            "education",
            {
                "institution": "Example University",
                "degree": "BSc",
                "field_of_study": "Analytics",
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
            },
            Education,
            "institution",
            "Example University",
        ),
    ],
)
def test_owner_can_create_edit_and_delete_each_content_type(
    tmp_path,
    monkeypatch,
    kind: str,
    form: dict,
    model,
    display_field: str,
    display_value: str,
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    _login(client)
    token = _csrf_token(client.get(f"/admin/{kind}/new"))
    created = client.post(
        f"/admin/{kind}/new",
        data={
            **form,
            "csrf_token": token,
            "display_order": "4",
            "is_visible": "on",
        },
    )

    assert created.status_code == 303
    with Session(create_database_engine(database_url)) as session:
        record = session.scalar(select(model))
        assert record is not None
        record_id = record.id
        assert getattr(record, display_field) == display_value
        assert record.display_order == 4
        assert record.is_visible is True

    edit_token = _csrf_token(client.get(f"/admin/{kind}/{record_id}/edit"))
    edited = client.post(
        f"/admin/{kind}/{record_id}/edit",
        data={
            **form,
            "csrf_token": edit_token,
            "display_order": "2",
        },
    )

    assert edited.status_code == 303
    with Session(create_database_engine(database_url)) as session:
        edited_record = session.get(model, record_id)
        assert edited_record is not None
        assert edited_record.display_order == 2
        assert edited_record.is_visible is False
    public_page = client.get("/")
    assert display_value not in public_page.text

    delete_token = _csrf_token(client.get(f"/admin/{kind}"))
    deleted = client.post(
        f"/admin/{kind}/{record_id}/delete",
        data={"csrf_token": delete_token},
    )

    assert deleted.status_code == 303
    with Session(create_database_engine(database_url)) as session:
        assert session.get(model, record_id) is None


def test_profile_can_be_edited_and_profile_urls_are_validated(
    tmp_path, monkeypatch
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    _login(client)
    token = _csrf_token(client.get("/admin/profile"))
    invalid = client.post(
        "/admin/profile",
        data={
            "csrf_token": token,
            "display_name": "Jordan Lee",
            "headline": "Analyst",
            "summary": "A summary.",
            "email": "",
            "website": "javascript:alert(1)",
            "linkedin_url": "",
            "github_url": "",
        },
    )

    assert invalid.status_code == 422
    assert "Website must be an http or https URL" in invalid.text

    valid = client.post(
        "/admin/profile",
        data={
            "csrf_token": token,
            "display_name": "Jordan Lee",
            "headline": "Analyst",
            "summary": "A summary.",
            "email": "jordan@example.com",
            "website": "https://jordan.example.com",
            "linkedin_url": "",
            "github_url": "",
        },
    )

    assert valid.status_code == 303
    with Session(create_database_engine(database_url)) as session:
        profile = session.scalar(select(Profile).where(Profile.slug == "owner"))
        assert profile is not None
        assert profile.display_name == "Jordan Lee"
        assert profile.website == "https://jordan.example.com"


def test_invalid_dates_are_reported_and_do_not_persist(
    tmp_path, monkeypatch
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    _login(client)
    token = _csrf_token(client.get("/admin/experiences/new"))
    response = client.post(
        "/admin/experiences/new",
        data={
            "csrf_token": token,
            "title": "Analyst",
            "company": "Example Co",
            "start_date": "not-a-date",
            "end_date": "2024-01-01",
        },
    )

    assert response.status_code == 422
    assert "Start date must be a valid date in YYYY-MM-DD format" in response.text
    with Session(create_database_engine(database_url)) as session:
        assert session.scalars(select(Experience)).all() == []


def test_public_page_honors_visibility_and_order_for_all_content(
    tmp_path, monkeypatch
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.slug == "owner"))
        assert profile is not None
        profile.experiences = [
            Experience(
                title="Second",
                company="Co",
                display_order=2,
                is_visible=True,
            ),
            Experience(
                title="First",
                company="Co",
                display_order=1,
                is_visible=True,
            ),
            Experience(
                title="Hidden",
                company="Co",
                display_order=0,
                is_visible=False,
            ),
        ]
        profile.skills = [
            Skill(name="Second Skill", display_order=2, is_visible=True),
            Skill(name="First Skill", display_order=1, is_visible=True),
            Skill(name="Hidden Skill", display_order=0, is_visible=False),
        ]
        profile.projects = [
            Project(name="Second Project", display_order=2, is_visible=True),
            Project(name="Hidden Project", display_order=0, is_visible=False),
        ]
        profile.education = [
            Education(
                institution="Visible Education",
                display_order=1,
                is_visible=True,
            ),
            Education(
                institution="Hidden Education",
                display_order=0,
                is_visible=False,
            ),
        ]
        session.commit()

    response = client.get("/")

    assert response.status_code == 200
    assert response.text.index("First</h3>") < response.text.index("Second</h3>")
    assert response.text.index("First Skill") < response.text.index("Second Skill")
    assert response.text.index("Second Project") < response.text.index(
        "Visible Education"
    )
    for hidden in (
        "Hidden",
        "Hidden Skill",
        "Hidden Project",
        "Hidden Education",
    ):
        assert hidden not in response.text
    assert "Second Project" in response.text
    assert "Visible Education" in response.text


def test_public_nested_skills_follow_display_order_and_omit_hidden_skills(
    tmp_path, monkeypatch
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.slug == "owner"))
        assert profile is not None
        first = Skill(name="Zebra Skill", display_order=1, is_visible=True)
        second = Skill(name="Alpha Skill", display_order=2, is_visible=True)
        hidden = Skill(name="Hidden Nested Skill", display_order=0, is_visible=False)
        profile.skills = [first, second, hidden]
        session.flush()
        session.add_all(
            [
                Experience(
                    profile_id=profile.id,
                    title="Role with ordered skills",
                    company="Example Co",
                    skills=[first, second, hidden],
                ),
                Project(
                    profile_id=profile.id,
                    name="Project with ordered skills",
                    skills=[first, second, hidden],
                ),
            ]
        )
        session.commit()

    response = client.get("/")

    assert response.status_code == 200
    experience_section = response.text.split('id="experience"', 1)[1].split(
        'id="skills"', 1
    )[0]
    project_section = response.text.split('id="projects"', 1)[1].split(
        'id="education"', 1
    )[0]
    for section in (experience_section, project_section):
        assert section.index("Zebra Skill") < section.index("Alpha Skill")
        assert "Hidden Nested Skill" not in section


def test_editing_experience_and_project_persists_skill_and_tag_associations(
    tmp_path, monkeypatch
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        profile = session.scalar(select(Profile).where(Profile.slug == "owner"))
        assert profile is not None
        original_skill = Skill(profile_id=profile.id, name="Original")
        replacement_skill = Skill(profile_id=profile.id, name="Replacement")
        session.add_all([original_skill, replacement_skill])
        session.flush()
        experience = Experience(
            profile_id=profile.id,
            title="Analyst",
            company="Example Co",
            skills=[original_skill],
        )
        project = Project(
            profile_id=profile.id,
            name="Portfolio",
            skills=[original_skill],
            tags=[ProjectTag(name="Original tag")],
        )
        session.add_all([experience, project])
        session.commit()
        experience_id = experience.id
        project_id = project.id

    _login(client)
    experience_token = _csrf_token(
        client.get(f"/admin/experiences/{experience_id}/edit")
    )
    experience_update = client.post(
        f"/admin/experiences/{experience_id}/edit",
        data={
            "csrf_token": experience_token,
            "title": "Analyst",
            "company": "Example Co",
            "skill_names": "Replacement",
            "display_order": "0",
            "is_visible": "on",
        },
    )
    project_token = _csrf_token(client.get(f"/admin/projects/{project_id}/edit"))
    project_update = client.post(
        f"/admin/projects/{project_id}/edit",
        data={
            "csrf_token": project_token,
            "name": "Portfolio",
            "skill_names": "Replacement",
            "tag_names": "Research, Dashboard",
            "display_order": "0",
            "is_visible": "on",
        },
    )

    assert experience_update.status_code == 303
    assert project_update.status_code == 303
    with Session(engine) as session:
        saved_experience = session.get(Experience, experience_id)
        saved_project = session.get(Project, project_id)
        assert saved_experience is not None
        assert saved_project is not None
        assert [skill.name for skill in saved_experience.skills] == ["Replacement"]
        assert [skill.name for skill in saved_project.skills] == ["Replacement"]
        assert {tag.name for tag in saved_project.tags} == {"Research", "Dashboard"}


def test_project_url_and_required_fields_are_rejected_with_field_errors(
    tmp_path, monkeypatch
) -> None:
    client, database_url = _client(tmp_path, monkeypatch)
    _login(client)
    token = _csrf_token(client.get("/admin/projects/new"))
    response = client.post(
        "/admin/projects/new",
        data={
            "csrf_token": token,
            "name": " ",
            "description": "",
            "url": "file:///etc/passwd",
        },
    )

    assert response.status_code == 422
    assert "Name is required" in response.text
    assert "Project URL must be an http or https URL" in response.text
    with Session(create_database_engine(database_url)) as session:
        assert session.scalars(select(Project)).all() == []
