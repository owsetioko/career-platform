import json
import logging
import os
import secrets
import tempfile
from contextlib import suppress
from datetime import date
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Generator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, selectinload
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from app.admin import build_admin_router, is_argon2id_hash
from app.database import (
    Experience,
    Profile,
    Project,
    create_database_engine,
    get_database_url,
)

APP_DIR = Path(__file__).resolve().parent
PROFILE_CACHE_PATH = APP_DIR.parent / "data" / "public-profile.json"
BUNDLED_FALLBACK_PATH = APP_DIR / "fallback-profile.json"
logger = logging.getLogger(__name__)
load_dotenv(APP_DIR.parent / ".env")

templates = Jinja2Templates(directory=APP_DIR / "templates")


@lru_cache
def _engine_for_url(database_url: str) -> Engine:
    return create_database_engine(database_url)


def get_session() -> Generator[Session, None, None]:
    with Session(_engine_for_url(get_database_url())) as session:
        yield session


def _serialize_profile(profile: Profile) -> dict:
    def date_value(value: date | None) -> str | None:
        return value.isoformat() if value else None

    return {
        "slug": profile.slug,
        "display_name": profile.display_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "email": profile.email,
        "website": profile.website,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "experiences": [
            {
                "title": experience.title,
                "company": experience.company,
                "location": experience.location,
                "description": experience.description,
                "start_date": date_value(experience.start_date),
                "end_date": date_value(experience.end_date),
                "skills": [
                    {"name": skill.name}
                    for skill in experience.skills
                    if skill.is_visible
                ],
            }
            for experience in profile.experiences
            if experience.is_visible
        ],
        "skills": [
            {"name": skill.name} for skill in profile.skills if skill.is_visible
        ],
        "projects": [
            {
                "name": project.name,
                "description": project.description,
                "url": project.url,
                "skills": [
                    {"name": skill.name}
                    for skill in project.skills
                    if skill.is_visible
                ],
                "tags": [{"name": tag.name} for tag in project.tags],
            }
            for project in profile.projects
            if project.is_visible
        ],
        "education": [
            {
                "institution": education.institution,
                "degree": education.degree,
                "field_of_study": education.field_of_study,
                "start_date": date_value(education.start_date),
                "end_date": date_value(education.end_date),
                "description": education.description,
            }
            for education in profile.education
            if education.is_visible
        ],
    }


def _hydrate_profile(data: dict) -> SimpleNamespace:
    def required_string(record: dict, key: str) -> str:
        value = record[key]
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        return value

    def optional_string(record: dict, key: str) -> str | None:
        value = record[key]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{key} must be a string or null")
        return value

    def parse_date(record: dict, key: str) -> date | None:
        value = optional_string(record, key)
        return date.fromisoformat(value) if value else None

    def records(key: str) -> list[dict]:
        value = data[key]
        if not isinstance(value, list) or any(
            not isinstance(record, dict) for record in value
        ):
            raise ValueError(f"{key} must be a list of objects")
        return value

    def skill_list(value: object) -> list[SimpleNamespace]:
        if not isinstance(value, list):
            raise ValueError("skills must be a list")
        if any(not isinstance(skill, dict) for skill in value):
            raise ValueError("skills must contain objects")
        return [
            SimpleNamespace(name=required_string(skill, "name")) for skill in value
        ]

    for key in (
        "slug",
        "display_name",
        "headline",
        "summary",
        "email",
        "website",
        "linkedin_url",
        "github_url",
        "experiences",
        "skills",
        "projects",
        "education",
    ):
        if key not in data:
            raise ValueError(f"missing profile field: {key}")

    return SimpleNamespace(
        slug=required_string(data, "slug"),
        display_name=required_string(data, "display_name"),
        headline=required_string(data, "headline"),
        summary=required_string(data, "summary"),
        email=optional_string(data, "email"),
        website=optional_string(data, "website"),
        linkedin_url=optional_string(data, "linkedin_url"),
        github_url=optional_string(data, "github_url"),
        experiences=[
            SimpleNamespace(
                title=required_string(record, "title"),
                company=required_string(record, "company"),
                location=optional_string(record, "location"),
                description=optional_string(record, "description"),
                start_date=parse_date(record, "start_date"),
                end_date=parse_date(record, "end_date"),
                skills=skill_list(record["skills"]),
            )
            for record in records("experiences")
        ],
        skills=skill_list(data["skills"]),
        projects=[
            SimpleNamespace(
                name=required_string(record, "name"),
                description=optional_string(record, "description"),
                url=optional_string(record, "url"),
                skills=skill_list(record["skills"]),
                tags=skill_list(record["tags"]),
            )
            for record in records("projects")
        ],
        education=[
            SimpleNamespace(
                institution=required_string(record, "institution"),
                degree=optional_string(record, "degree"),
                field_of_study=optional_string(record, "field_of_study"),
                start_date=parse_date(record, "start_date"),
                end_date=parse_date(record, "end_date"),
                description=optional_string(record, "description"),
            )
            for record in records("education")
        ],
    )


def _read_snapshot(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("profile snapshot must be an object")
        _hydrate_profile(data)
        return data
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        KeyError,
    ) as error:
        logger.warning(
            "Could not read usable public profile snapshot from %s: %s",
            path,
            error,
            exc_info=True,
        )
        return None


def _write_snapshot(data: dict) -> None:
    temporary_path: Path | None = None
    try:
        PROFILE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=PROFILE_CACHE_PATH.parent,
            prefix=f".{PROFILE_CACHE_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, ensure_ascii=False)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, PROFILE_CACHE_PATH)
    except Exception:
        logger.exception(
            "Could not refresh public profile cache at %s", PROFILE_CACHE_PATH
        )
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)


def _fallback_data() -> tuple[dict, str]:
    cached_data = _read_snapshot(PROFILE_CACHE_PATH)
    if cached_data is not None:
        return cached_data, "saved profile snapshot"

    try:
        bundled_data = json.loads(BUNDLED_FALLBACK_PATH.read_text(encoding="utf-8"))
        if not isinstance(bundled_data, dict):
            raise ValueError("bundled profile fallback must be an object")
        _hydrate_profile(bundled_data)
        return bundled_data, "starter profile"
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        KeyError,
    ):
        logger.exception("Bundled public profile fallback is unavailable")
        raise HTTPException(
            status_code=500, detail="Profile fallback is unavailable"
        ) from None


def _render_profile(request: Request, data: dict, fallback_source: str | None = None):
    profile = _hydrate_profile(data)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "profile": profile,
            "page_title": " | ".join(
                value for value in (profile.display_name, profile.headline) if value
            ),
            "page_description": profile.summary
            or profile.headline
            or profile.display_name,
            "fallback_source": fallback_source,
        },
    )


def create_app() -> FastAPI:
    session_secret = os.getenv("SESSION_SECRET", "")
    password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    session_configured = len(session_secret.encode("utf-8")) >= 32
    hash_configured = is_argon2id_hash(password_hash)
    application = FastAPI(title=os.getenv("APP_TITLE", "Personal Resume Platform"))
    application.state.admin_configured = session_configured and hash_configured
    application.state.admin_password_hash = password_hash
    application.add_middleware(
        SessionMiddleware,
        secret_key=session_secret or secrets.token_urlsafe(48),
        session_cookie="resume_session",
        same_site="lax",
        https_only=os.getenv("SESSION_COOKIE_SECURE", "").strip().lower()
        in {"1", "true", "yes", "on"},
    )
    application.mount(
        "/static",
        StaticFiles(directory=APP_DIR / "static"),
        name="static",
    )

    @application.get("/")
    async def home(request: Request, session: Session = Depends(get_session)):
        statement = (
            select(Profile)
            .where(Profile.slug == "owner")
            .options(
                selectinload(Profile.experiences).selectinload(Experience.skills),
                selectinload(Profile.skills),
                selectinload(Profile.projects).selectinload(Project.skills),
                selectinload(Profile.projects).selectinload(Project.tags),
                selectinload(Profile.education),
            )
        )
        try:
            profile = session.scalar(statement)
            if profile is None:
                raise HTTPException(status_code=404, detail="Public profile not found")
            public_data = _serialize_profile(profile)
        except DBAPIError:
            logger.exception("Public profile database read failed")
            fallback_data, fallback_source = _fallback_data()
            return _render_profile(request, fallback_data, fallback_source)

        _write_snapshot(public_data)
        return _render_profile(request, public_data)

    application.include_router(build_admin_router(templates, get_session))
    return application


app = create_app()
