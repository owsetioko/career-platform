import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR.parent / ".env")

app = FastAPI(title=os.getenv("APP_TITLE", "Personal Resume Platform"))
app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static",
)
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_title": app.title},
    )
