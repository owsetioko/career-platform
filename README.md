# Personal Resume Platform

A Codespaces-first starter app built with FastAPI, Jinja2, and plain CSS.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m app.database
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In Codespaces, open the forwarded port 8000 to view the app. The root page
renders the Jinja2 app shell; its stylesheet is served from `/static`.
The database initializer creates the SQLite schema and an editable starter
profile with placeholder content. It is safe to run more than once. By default,
the database is stored in the ignored `data/resume.db`; set `DATABASE_URL` in
`.env` to use a different SQLAlchemy database URL.

## Run tests

```bash
python -m pytest
```

The environment file configures the app title and database URL. The storage
layer includes profile, experience, skill, project, project-tag, and education
records. Public profile rendering, admin features, and deployment configuration
are separate follow-up tasks.