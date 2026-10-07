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

In Codespaces, open the forwarded port 8000 to view the public profile. Run
`python -m app.database` before starting the app to initialize the SQLite schema
and editable `owner` profile. The initializer is safe to run more than once. Its
starter profile contains placeholder values; replace them and add real profile
records before sharing the page. The profile is rendered from the database and
its stylesheet is served from `/static`. If a public profile database read
fails, the page uses the last-known-good snapshot at the ignored
`data/public-profile.json`; if no usable snapshot exists yet, the bundled
starter profile keeps the page available with clearly marked placeholders.
Successful reads refresh the snapshot atomically. By default, the database is
stored in the ignored `data/resume.db`; set `DATABASE_URL` in `.env` to use a
different SQLAlchemy database URL.

## Run tests

```bash
python -m pytest
```

The environment file configures the app title and database URL. The storage
layer includes profile, experience, skill, project, project-tag, and education
records. Admin features and deployment configuration are separate follow-up
tasks.