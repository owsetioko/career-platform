# Task 5 — Secure owner admin and content editing

## Result

Implemented the single-owner, server-rendered admin flow for the FastAPI,
Jinja2, and SQLAlchemy application. Public profile behavior and its cached and
bundled database-outage fallbacks remain in place.

## Delivered

- Added an admin application factory and `/admin` routes for login, logout,
  dashboard, profile editing, and create/list/edit/delete operations for
  experience, skills, projects, and education.
- Password verification accepts a valid Argon2id PHC hash from
  `ADMIN_PASSWORD_HASH`. Admin is explicitly unavailable with HTTP 503 unless
  a valid hash and a `SESSION_SECRET` of at least 32 bytes are configured.
- Added signed, HttpOnly, SameSite=Lax session cookies; the
  `SESSION_COOKIE_SECURE` setting can enable the Secure attribute for HTTPS.
  Successful login rotates session state. Logout and every other state-changing
  form require a session-bound CSRF token.
- Added server-rendered admin templates and plain CSS. Content forms support
  required fields, validated dates and HTTP(S) URLs, skill/tag associations,
  visibility, and display ordering. Invalid values render explicit field-level
  errors with HTTP 422 and are not saved.
- Public serialization now orders experience, skills, projects, and education
  by their display-order values and omits hidden records, including hidden
  skills attached to experiences and projects.
- Added backward-compatible SQLite column additions for existing experience,
  skill, project, and education tables. Existing rows receive display order
  zero and visible status by default.
- Documented safe local admin setup and Argon2id hash/signing-key generation in
  `README.md`. No password or signing key was added to source control.
- Added dependencies for Argon2, signed sessions, and URL-encoded form parsing.

## Test-first evidence

The implementation was driven by failing tests before the corresponding
production changes:

- Admin configuration/auth tests first failed because the admin app factory
  and routes did not exist.
- The legacy SQLite migration test failed because existing tables lacked the
  requested `display_order` and `is_visible` columns.
- A configuration regression test first returned HTTP 200 for a malformed
  Argon2id hash instead of the required HTTP 503; hash-format validation fixed
  that fail-open configuration case.

## Final verification

- Focused command:
  `python -m pytest --basetemp=data/task5-focused-final tests/test_admin.py tests/test_database.py -q --tb=short`
  — **32 passed**.
- Full command:
  `python -m pytest --basetemp=data/task5-full-final -q --tb=short`
  — **47 passed**.
- `python -m compileall -q app tests` — passed.
- `git diff --check` — passed.
- Tests cover unconfigured service behavior with public-page availability,
  missing/invalid credentials, successful and rejected login, unauthenticated
  page/write access, tampered signed cookies, CSRF rejection, secure-cookie
  configuration, logout, parameterized CRUD for all four content types,
  profile editing, invalid required/date/URL input, ordering/visibility, and
  migration of all legacy content tables.

## Scope and setup notes

No Azure deployment or GitHub push was performed. Configure the admin values
in the ignored local `.env` or a secret manager; keep the password itself out
of configuration and never commit either generated value. For HTTPS, set
`SESSION_COOKIE_SECURE=true`; the local HTTP default is false.
