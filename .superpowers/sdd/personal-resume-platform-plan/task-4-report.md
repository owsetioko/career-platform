# Task 4 — Public profile fallback during database outages

## Status

Implemented in the requested worktree. Scope was limited to keeping the public
profile visible through database outages; no admin/auth work, deployment work,
or database migrations were added.

## Design and behavior

- Successful profile reads are serialized to `data/public-profile.json`, which
  is already under the ignored persistent `data/` directory. Cache refreshes
  write a temporary file alongside the target and atomically replace the
  snapshot.
- Only SQLAlchemy `DBAPIError` database failures trigger profile fallback.
  Missing profiles still return 404 and are not replaced with cached content.
- Outages use a valid last-known-good snapshot first. Missing, unreadable, or
  invalid cached snapshots are logged and treated as unavailable; the bundled
  `app/fallback-profile.json` is used if valid.
- If the bundled fallback itself is unavailable or invalid, the page returns
  an explicit HTTP 500 response (`Profile fallback is unavailable`) rather
  than rendering an empty/success-shaped page.
- Live response rendering is not blocked by cache write failures; those are
  logged. Fallback pages display a visible status message.
- The bundled fallback contains only the known `Business Analytics Senior`
  headline and explicit name/summary placeholders. Experience, skills,
  projects, education, and contact information remain empty.

## TDD evidence

### RED

Before implementation, added focused cases to `tests/test_app.py` for first-run
outage, cached fallback, live-read cache refresh and reuse, cache-write
failure, missing-profile behavior, and invalid fallback data. Ran:

```text
python -m pytest tests/test_app.py -q
.......FFFF.FFF [100%]
7 failed, 8 passed
```

The new fallback cases failed because the public handler did not yet recover
from the simulated SQLAlchemy `OperationalError`, render/cache snapshots, or
report unusable bundled fallback data explicitly. Existing public rendering
cases continued to pass.

### GREEN

After implementing the fallback and cache paths, the focused suite passed:

```text
python -m pytest tests/test_app.py -q
15 passed
```

After the final exception-scope and test-isolation refinements, verification
was repeated:

```text
python -m pytest tests/test_app.py -q
15 passed

python -m pytest -q
22 passed

git diff --check
passed
```

## Changed files

- `app/main.py` — profile snapshot serialization/validation, atomic writes,
  narrowly scoped database fallback, explicit logging, and missing/corrupt
  data handling.
- `app/fallback-profile.json` — bundled, truthful starter fallback.
- `app/templates/index.html` and `app/static/css/styles.css` — visible fallback
  status.
- `tests/test_app.py` — focused outage, caching, error, and no-fake-profile
  coverage.
- `README.md` — documents snapshot and first-run fallback behavior.

## Remaining concerns

- Admin editing is intentionally not addressed and may remain unavailable
  during a database outage, as permitted by the task brief.
- A fallback HTTP 500 is intentional if both the persisted snapshot and
  bundled fallback are unusable; operators should repair the packaged fallback
  rather than receive a fabricated public profile.
