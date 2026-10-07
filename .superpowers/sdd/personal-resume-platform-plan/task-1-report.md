# Task 1 implementation and TDD evidence

## Implementation

Added a Codespaces-first starter app using FastAPI, Jinja2, and plain CSS:

- `app/main.py` creates the FastAPI app, loads the optional local `.env`, mounts
  static files, and renders the root page from a Jinja2 template.
- `app/templates/index.html` provides the minimal app shell and links its
  stylesheet through FastAPI's named static mount.
- `app/static/css/styles.css` styles the responsive shell without a CSS
  framework or external asset dependency.
- `app/__init__.py` makes `app` importable as a Python package.
- `requirements.txt` lists runtime dependencies; `requirements-dev.txt` adds
  HTTP test and pytest dependencies.
- `.env.example` contains only the configurable app title. `.env` is already
  ignored by Git.
- `README.md` documents setup, running the app on the Codespaces-forwarded
  port, and running the test.
- `tests/test_app.py` smoke-tests the root route's status, HTML content type,
  and app-shell heading.

No database was created or connected. No profile content, admin/auth behavior,
or Azure deployment setup was added.

## TDD evidence

The root-route test was written before the application module. The first
attempt from the worktree, after declaring and installing the test/runtime
dependencies, produced the expected red result:

```text
tests/test_app.py:3: in <module>
    from app.main import app
E   ModuleNotFoundError: No module named 'app'
1 error in 1.04s
```

After implementing the app shell, the focused test passed:

```text
$ python -m pytest -q tests/test_app.py
.                                                                        [100%]
1 passed in 0.41s
```

The module invocation is documented because this environment's standalone
`pytest` entry point does not add the current project directory to `sys.path`;
`python -m pytest` does.

## Local HTTP smoke check

Started Uvicorn locally and requested both the home page and the stylesheet.
Both `curl --fail` requests succeeded. The HTML included the expected title,
heading, and stylesheet URL; the stylesheet response included the `.app-shell`
rule.
