# Personal Resume Platform

A Codespaces-first starter app built with FastAPI, Jinja2, and plain CSS.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In Codespaces, open the forwarded port 8000 to view the app. The root page
renders the Jinja2 app shell; its stylesheet is served from `/static`.

## Run tests

```bash
python -m pytest
```

The environment file only configures the app title. Database, profile, admin,
and deployment features are intentionally not part of this starter phase.