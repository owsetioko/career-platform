import os
from functools import lru_cache
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload
from starlette.templating import Jinja2Templates

from app.database import (
    Experience,
    Profile,
    Project,
    create_database_engine,
    get_database_url,
)

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR.parent / ".env")

app = FastAPI(title=os.getenv("APP_TITLE", "Personal Resume Platform"))
app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static",
)
templates = Jinja2Templates(directory=APP_DIR / "templates")


@lru_cache
def _engine_for_url(database_url: str) -> Engine:
    return create_database_engine(database_url)


def get_session() -> Generator[Session, None, None]:
    with Session(_engine_for_url(get_database_url())) as session:
        yield session


@app.get("/")
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
    profile = session.scalar(statement)
    if profile is None:
        raise HTTPException(status_code=404, detail="Public profile not found")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "profile": profile,
            "page_title": " | ".join(
                value
                for value in (profile.display_name, profile.headline)
                if value
            ),
            "page_description": profile.summary
            or profile.headline
            or profile.display_name,
        },
    )
