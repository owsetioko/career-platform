# Task 3 implementation and TDD report

## Outcome

Implemented the public recruiter-facing profile page using persisted SQLite
records and Jinja2. The page renders the profile, experience, skills, projects,
and education in that order, with semantic section headings and readable
collection empty states. It uses the existing database models and configured
`DATABASE_URL`; it does not initialize missing databases, fabricate profile
records, or add a database-outage fallback.

## Implementation

- Added a request-scoped SQLAlchemy `Session` dependency backed by a cached
  engine created through `app.database.create_database_engine()` and
  `get_database_url()`.
- The root route retrieves the `Profile` with slug `owner` and loads its
  experience, skills, projects, project tags, and education relationships.
  It returns 404 when that profile is absent.
- Replaced the starter shell with a semantic Jinja2 profile. The title and
  description metadata are generated from stored profile values. Optional
  summaries and collections have explicit empty states; optional record fields
  and project links appear only when stored. A missing end date is not
  presented as proof that a role or education is ongoing.
- Replaced the centered starter styling with recruiter-scannable profile
  sections, responsive plain CSS, and a small-screen breakpoint. Core content
  requires no JavaScript.
- Updated the README/Codespaces instructions to initialize the database before
  starting the server and warned that starter placeholder profile data must be
  replaced before sharing.
- The current database schema has no contact fields; consequently, the page
  does not invent contact links.

## TDD evidence

1. Updated `tests/test_app.py` before implementing the route or template. The
   tests inserted a profile and related records into a temporary SQLite
   database and requested the public page; they also checked optional values
   and the responsive stylesheet.
2. Ran the focused tests before implementation:
   `python -m pytest tests/test_app.py -q` — **RED**, 3 failed. The new persisted
   profile and optional-content assertions failed against the starter shell;
   the CSS assertion found no responsive media rule.
3. During implementation, added a regression assertion that a missing end date
   is not rendered as “Present.” Ran that focused test before changing the
   template — **RED**, 1 failed because the page inferred an unrecorded
   employment/education status. Removed that inference.
4. Focused verification after implementation:
   `python -m pytest tests/test_app.py -q --basetemp=.pytest-tmp` — **4 passed**.
5. Full verification:
   `python -m pytest -q --basetemp=.pytest-tmp` — **9 passed**.
6. `git diff --check` completed successfully. The focused suite verifies stored
   profile, experience, skill, project, project-tag, and education content in
   the rendered response and verifies `/static/css/styles.css` returns CSS
   containing responsive rules.

## Scope notes

No admin/auth features, database-outage recovery, JavaScript dependency, or
deployment changes were added.

## Commit

`3df379d822b0ab8721b94c3f5b0bdca0a9096ad9 feat: render public recruiter profile page`

## Contact omission fix

### What changed

- Added optional, nullable `email`, `website`, `linkedin_url`, and `github_url`
  columns to `Profile`; all four values persist through SQLite. Database
  initialization also adds these nullable columns to an existing profile table,
  so a previously initialized SQLite database remains usable.
- Added an accessible, semantic Contact section with clearly named links for
  configured contact values only. Email uses a `mailto:` link. When no contact
  values are configured, the section remains visible and states: “No contact
  methods have been provided.”
- Styled contact actions with plain CSS.
- Added database round-trip coverage and public-page tests for all configured
  link types, omitted unconfigured links, and the empty state.

### TDD and verification

From `/workspaces/career-platform/.worktrees/personal-resume-task1`:

1. RED:
   `python -m pytest tests/test_database.py::test_profile_contact_fields_round_trip tests/test_app.py::test_public_profile_shows_only_configured_contact_links tests/test_app.py::test_public_profile_shows_truthful_empty_contact_state -q`
   — **3 failed**. The persistence and configured-link tests failed because
   `Profile` did not accept `email`; the empty-state test failed because the
   Contact section was absent.
2. Focused GREEN:
   `python -m pytest tests/test_database.py::test_profile_contact_fields_round_trip tests/test_app.py -q --basetemp=.pytest-tmp`
   — **8 passed**.
3. Full suite:
   `python -m pytest -q --basetemp=.pytest-tmp` — **13 passed**.
4. `git diff --check` — **passed**.

All route tests use temporary SQLite databases; the persistence round-trip
uses SQLite in-memory storage.

### Existing-database schema update

Added a regression test that creates the pre-contact SQLite `profiles` schema
and verifies initialization adds the four optional columns without losing the
stored profile. The test also writes and reloads an email value after the
update.

- RED: `python -m pytest tests/test_database.py::test_initialization_adds_contact_fields_to_existing_sqlite_profile -q --basetemp=.pytest-tmp`
  — **1 failed** with `sqlite3.OperationalError: no such column:
  profiles.email`.
- GREEN and focused contact checks:
  `python -m pytest tests/test_database.py::test_initialization_adds_contact_fields_to_existing_sqlite_profile tests/test_database.py::test_profile_contact_fields_round_trip tests/test_app.py -q --basetemp=.pytest-tmp`
  — **9 passed**.
- Full suite: `python -m pytest -q --basetemp=.pytest-tmp` — **14 passed**.
- `git diff --check` — **passed**.
