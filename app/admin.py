from __future__ import annotations

import re
import secrets
from datetime import date
from email.utils import parseaddr
from typing import Callable
from urllib.parse import urlsplit

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from app.database import (
    Education,
    Experience,
    Profile,
    Project,
    ProjectTag,
    Skill,
)

CONTENT_TYPES = {
    "experiences": {
        "label": "Experience",
        "model": Experience,
        "fields": (
            ("title", "Job title", "text", True, 200),
            ("company", "Company", "text", True, 200),
            ("location", "Location", "text", False, 200),
            ("description", "Description", "textarea", False, 4000),
            ("start_date", "Start date", "date", False, 0),
            ("end_date", "End date", "date", False, 0),
            ("skill_names", "Skills (comma-separated)", "text", False, 2000),
        ),
    },
    "skills": {
        "label": "Skill",
        "model": Skill,
        "fields": (("name", "Name", "text", True, 120),),
    },
    "projects": {
        "label": "Project",
        "model": Project,
        "fields": (
            ("name", "Name", "text", True, 200),
            ("description", "Description", "textarea", False, 4000),
            ("url", "Project URL", "url", False, 1000),
            ("skill_names", "Skills (comma-separated)", "text", False, 2000),
            ("tag_names", "Tags (comma-separated)", "text", False, 2000),
        ),
    },
    "education": {
        "label": "Education",
        "model": Education,
        "fields": (
            ("institution", "Institution", "text", True, 200),
            ("degree", "Degree", "text", False, 200),
            ("field_of_study", "Field of study", "text", False, 200),
            ("start_date", "Start date", "date", False, 0),
            ("end_date", "End date", "date", False, 0),
            ("description", "Description", "textarea", False, 4000),
        ),
    },
}

PROFILE_FIELDS = (
    ("display_name", "Display name", "text", True, 160),
    ("headline", "Headline", "text", True, 240),
    ("summary", "Summary", "textarea", False, 2000),
    ("email", "Email", "email", False, 320),
    ("website", "Website", "url", False, 1000),
    ("linkedin_url", "LinkedIn URL", "url", False, 1000),
    ("github_url", "GitHub URL", "url", False, 1000),
)


def is_argon2id_hash(value: str) -> bool:
    try:
        return extract_parameters(value).type == Type.ID
    except (InvalidHashError, TypeError, ValueError):
        return False


def _admin_configured(request: Request) -> None:
    if not request.app.state.admin_configured:
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin is not configured. Set ADMIN_PASSWORD_HASH and "
                "SESSION_SECRET to enable owner access."
            ),
        )


def _require_authenticated(request: Request) -> None:
    _admin_configured(request)
    if request.session.get("authenticated") is not True:
        raise HTTPException(
            status_code=303,
            detail="Authentication required",
            headers={"Location": "/admin/login"},
        )


def _csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not isinstance(token, str):
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


async def _validated_form(request: Request) -> dict[str, str]:
    form = await request.form()
    expected = request.session.get("csrf_token")
    supplied = form.get("csrf_token")
    if (
        not isinstance(expected, str)
        or not isinstance(supplied, str)
        or not secrets.compare_digest(expected, supplied)
    ):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token")
    return {
        key: value.strip() if isinstance(value, str) else ""
        for key, value in form.multi_items()
        if isinstance(value, str)
    }


def _render(
    templates: Jinja2Templates,
    request: Request,
    name: str,
    context: dict,
    *,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={"csrf_token": _csrf_token(request), **context},
        status_code=status_code,
    )


def _profile(session: Session) -> Profile:
    profile = session.scalar(select(Profile).where(Profile.slug == "owner"))
    if profile is None:
        raise HTTPException(status_code=404, detail="Owner profile not found")
    return profile


def _field_definitions(fields: tuple) -> list[dict]:
    return [
        {
            "name": name,
            "label": label,
            "type": field_type,
            "required": required,
            "max_length": max_length or None,
        }
        for name, label, field_type, required, max_length in fields
    ]


def _raw_values(form: dict[str, str], fields: tuple) -> dict[str, str]:
    names = [field[0] for field in fields]
    names.extend(("display_order", "skill_names", "tag_names"))
    return {name: form.get(name, "") for name in names}


def _validate_url(value: str, label: str, errors: list[str]) -> str | None:
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        valid_port = parsed.port is None or 0 < parsed.port <= 65535
        valid = (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and valid_port
            and not any(character.isspace() for character in value)
        )
    except ValueError:
        valid = False
    if not valid:
        errors.append(f"{label} must be an http or https URL")
        return None
    return value


def _validate_fields(
    form: dict[str, str], fields: tuple, *, validate_order: bool = False
) -> tuple[dict, list[str]]:
    values: dict = {}
    errors: list[str] = []
    for name, label, field_type, required, max_length in fields:
        value = form.get(name, "").strip()
        if required and not value:
            errors.append(f"{label} is required")
            continue
        if max_length and len(value) > max_length:
            errors.append(f"{label} must be no more than {max_length} characters")
            continue
        if field_type == "date":
            if value:
                try:
                    values[name] = date.fromisoformat(value)
                except ValueError:
                    errors.append(
                        f"{label} must be a valid date in YYYY-MM-DD format"
                    )
            else:
                values[name] = None
        elif field_type == "url":
            values[name] = _validate_url(value, label, errors)
        elif field_type == "email":
            if value and (
                parseaddr(value)[1] != value
                or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value)
            ):
                errors.append("Email must be a valid email address")
            values[name] = value or None
        else:
            values[name] = value

    start_date = values.get("start_date")
    end_date = values.get("end_date")
    if start_date and end_date and start_date > end_date:
        errors.append("End date must not be before start date")

    for field_name, label, max_length in (
        ("skill_names", "Skill names", 120),
        ("tag_names", "Tag names", 80),
    ):
        if field_name in form:
            too_long = any(
                len(name) > max_length for name in _split_names(form[field_name])
            )
            if too_long:
                errors.append(f"{label} must be no more than {max_length} characters")

    if validate_order:
        try:
            display_order = int(form.get("display_order", "0"))
            if not 0 <= display_order <= 1_000_000:
                raise ValueError
            values["display_order"] = display_order
        except ValueError:
            errors.append("Display order must be a whole number from 0 to 1000000")
        values["is_visible"] = form.get("is_visible", "").lower() in {
            "on",
            "true",
            "1",
        }
    return values, errors


def _split_names(value: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for item in value.split(","):
        name = item.strip()
        if name and name.casefold() not in seen:
            names.append(name)
            seen.add(name.casefold())
    return names


def _associated_skills(
    session: Session, profile: Profile, values: dict
) -> list[Skill] | None:
    if "skill_names" not in values:
        return None
    skills: list[Skill] = []
    for name in _split_names(values["skill_names"]):
        skill = session.scalar(
            select(Skill).where(
                Skill.profile_id == profile.id,
                Skill.name == name,
            )
        )
        if skill is None:
            skill = Skill(profile_id=profile.id, name=name)
            session.add(skill)
        skills.append(skill)
    return skills


def _apply_content_values(
    session: Session,
    profile: Profile,
    kind: str,
    record,
    values: dict,
) -> None:
    custom = {"skill_names", "tag_names"}
    for name, value in values.items():
        if name not in custom:
            setattr(record, name, value)
    skills = _associated_skills(session, profile, values)
    if skills is not None and kind in {"experiences", "projects"}:
        record.skills = skills
    if kind == "projects" and "tag_names" in values:
        record.tags = [
            ProjectTag(name=name) for name in _split_names(values["tag_names"])
        ]


def _form_values(record, fields: tuple) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, _label, field_type, *_ in fields:
        if name == "skill_names":
            values[name] = ", ".join(skill.name for skill in record.skills)
        elif name == "tag_names":
            values[name] = ", ".join(tag.name for tag in record.tags)
        else:
            value = getattr(record, name, None)
            values[name] = value.isoformat() if field_type == "date" and value else (
                value or ""
            )
    values["display_order"] = str(record.display_order)
    values["is_visible"] = "on" if record.is_visible else ""
    return values


def _content_form_context(
    kind: str,
    spec: dict,
    record_id: int | None,
    values: dict[str, str],
    errors: list[str],
) -> dict:
    return {
        "kind": kind,
        "label": spec["label"],
        "record_id": record_id,
        "fields": _field_definitions(spec["fields"]),
        "values": values,
        "errors": errors,
        "is_visible": values.get("is_visible") in {"on", "true", "1"},
    }


def _save_content(
    session: Session,
    profile: Profile,
    kind: str,
    spec: dict,
    record,
    values: dict,
) -> str | None:
    if record is None:
        record = spec["model"](profile_id=profile.id)
        session.add(record)
    _apply_content_values(session, profile, kind, record, values)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return "A record with these values already exists"
    return None


def build_admin_router(
    templates: Jinja2Templates,
    session_dependency: Callable,
) -> APIRouter:
    router = APIRouter(prefix="/admin", dependencies=[Depends(_admin_configured)])
    password_hasher = PasswordHasher()

    @router.get("/login")
    async def login_page(request: Request):
        return _render(templates, request, "admin_login.html", {"error": None})

    @router.post("/login")
    async def login(request: Request):
        form = await _validated_form(request)
        password = form.get("password", "")
        stored_hash = request.app.state.admin_password_hash
        try:
            authenticated = len(password) <= 1024 and password_hasher.verify(
                stored_hash, password
            )
        except VerificationError:
            authenticated = False
        if not authenticated:
            return _render(
                templates,
                request,
                "admin_login.html",
                {"error": "Invalid password"},
                status_code=401,
            )

        request.session.clear()
        request.session["authenticated"] = True
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        return RedirectResponse("/admin", status_code=303)

    @router.post("/logout")
    async def logout(request: Request):
        _require_authenticated(request)
        await _validated_form(request)
        request.session.clear()
        return RedirectResponse("/admin/login", status_code=303)

    @router.get("")
    @router.get("/")
    async def dashboard(
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        profile = _profile(session)
        counts = {
            kind: session.query(spec["model"])
            .filter(spec["model"].profile_id == profile.id)
            .count()
            for kind, spec in CONTENT_TYPES.items()
        }
        return _render(
            templates,
            request,
            "admin_dashboard.html",
            {"profile": profile, "counts": counts},
        )

    @router.get("/profile")
    async def profile_form(
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        profile = _profile(session)
        return _render(
            templates,
            request,
            "admin_profile_form.html",
            {
                "profile": profile,
                "fields": _field_definitions(PROFILE_FIELDS),
                "values": {
                    field[0]: getattr(profile, field[0]) or ""
                    for field in PROFILE_FIELDS
                },
                "errors": [],
            },
        )

    @router.post("/profile")
    async def update_profile(
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        form = await _validated_form(request)
        values, errors = _validate_fields(form, PROFILE_FIELDS)
        profile = _profile(session)
        if errors:
            return _render(
                templates,
                request,
                "admin_profile_form.html",
                {
                    "profile": profile,
                    "fields": _field_definitions(PROFILE_FIELDS),
                    "values": _raw_values(form, PROFILE_FIELDS),
                    "errors": errors,
                },
                status_code=422,
            )
        for name, value in values.items():
            setattr(profile, name, value)
        session.commit()
        return RedirectResponse("/admin", status_code=303)

    @router.get("/{kind}")
    async def content_list(
        kind: str,
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        spec = CONTENT_TYPES.get(kind)
        if spec is None:
            raise HTTPException(status_code=404, detail="Content type not found")
        profile = _profile(session)
        records = session.scalars(
            select(spec["model"])
            .where(spec["model"].profile_id == profile.id)
            .order_by(spec["model"].display_order, spec["model"].id)
        ).all()
        return _render(
            templates,
            request,
            "admin_list.html",
            {"kind": kind, "spec": spec, "records": records},
        )

    @router.get("/{kind}/new")
    async def new_content_form(
        kind: str,
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        spec = CONTENT_TYPES.get(kind)
        if spec is None:
            raise HTTPException(status_code=404, detail="Content type not found")
        return _render(
            templates,
            request,
            "admin_form.html",
            _content_form_context(
                kind,
                spec,
                None,
                {"display_order": "0", "is_visible": "on"},
                [],
            ),
        )

    @router.post("/{kind}/new")
    async def create_content(
        kind: str,
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        spec = CONTENT_TYPES.get(kind)
        if spec is None:
            raise HTTPException(status_code=404, detail="Content type not found")
        form = await _validated_form(request)
        values, errors = _validate_fields(
            form, spec["fields"], validate_order=True
        )
        profile = _profile(session)
        if errors:
            return _render(
                templates,
                request,
                "admin_form.html",
                _content_form_context(
                    kind, spec, None, _raw_values(form, spec["fields"]), errors
                ),
                status_code=422,
            )
        save_error = _save_content(session, profile, kind, spec, None, values)
        if save_error:
            return _render(
                templates,
                request,
                "admin_form.html",
                _content_form_context(
                    kind,
                    spec,
                    None,
                    _raw_values(form, spec["fields"]),
                    [save_error],
                ),
                status_code=422,
            )
        return RedirectResponse(f"/admin/{kind}", status_code=303)

    @router.get("/{kind}/{record_id}/edit")
    async def edit_content_form(
        kind: str,
        record_id: int,
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        spec = CONTENT_TYPES.get(kind)
        if spec is None:
            raise HTTPException(status_code=404, detail="Content type not found")
        profile = _profile(session)
        record = session.scalar(
            select(spec["model"]).where(
                spec["model"].id == record_id,
                spec["model"].profile_id == profile.id,
            )
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Content record not found")
        values = _form_values(record, spec["fields"])
        return _render(
            templates,
            request,
            "admin_form.html",
            _content_form_context(kind, spec, record.id, values, []),
        )

    @router.post("/{kind}/{record_id}/edit")
    async def update_content(
        kind: str,
        record_id: int,
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        spec = CONTENT_TYPES.get(kind)
        if spec is None:
            raise HTTPException(status_code=404, detail="Content type not found")
        form = await _validated_form(request)
        values, errors = _validate_fields(
            form, spec["fields"], validate_order=True
        )
        profile = _profile(session)
        record = session.scalar(
            select(spec["model"]).where(
                spec["model"].id == record_id,
                spec["model"].profile_id == profile.id,
            )
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Content record not found")
        if errors:
            return _render(
                templates,
                request,
                "admin_form.html",
                _content_form_context(
                    kind,
                    spec,
                    record.id,
                    _raw_values(form, spec["fields"]),
                    errors,
                ),
                status_code=422,
            )
        save_error = _save_content(session, profile, kind, spec, record, values)
        if save_error:
            return _render(
                templates,
                request,
                "admin_form.html",
                _content_form_context(
                    kind,
                    spec,
                    record_id,
                    _raw_values(form, spec["fields"]),
                    [save_error],
                ),
                status_code=422,
            )
        return RedirectResponse(f"/admin/{kind}", status_code=303)

    @router.post("/{kind}/{record_id}/delete")
    async def delete_content(
        kind: str,
        record_id: int,
        request: Request,
        session: Session = Depends(session_dependency),
    ):
        _require_authenticated(request)
        await _validated_form(request)
        spec = CONTENT_TYPES.get(kind)
        if spec is None:
            raise HTTPException(status_code=404, detail="Content type not found")
        profile = _profile(session)
        record = session.scalar(
            select(spec["model"]).where(
                spec["model"].id == record_id,
                spec["model"].profile_id == profile.id,
            )
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Content record not found")
        session.delete(record)
        session.commit()
        return RedirectResponse(f"/admin/{kind}", status_code=303)

    return router
