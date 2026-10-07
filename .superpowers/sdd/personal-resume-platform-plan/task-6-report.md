# Task 6 — Final local validation and Azure VM readiness report

**Date:** 2026-10-07
**Worktree:** `/workspaces/career-platform/.worktrees/personal-resume-task1`
**Scope:** Final local validation and beginner-friendly setup/future Azure VM
documentation only. No Azure resources were created and nothing was deployed
or pushed.

## Documentation completed

Reworked `README.md` to describe:

- Starting from a Codespace, setting up Python and dependencies, creating
  `.env`, initializing SQLite, starting the app, and opening the forwarded
  port.
- The default database and cache locations, the repeatable database
  initializer, the public fallback behavior, and running the complete tests.
- Creating an Argon2id admin password hash and a random session secret,
  configuring secure cookies for HTTPS, and using the admin dashboard.
- Common setup, port, database, admin-configuration, cookie, and content
  visibility problems.
- Future single-VM Azure readiness: supported Python runtime, persistent disk
  and file paths, protected secrets, a dedicated service account and sample
  systemd unit, initialization/start/restart/log commands, HTTPS/reverse
  proxy and trusted forwarded headers, NSG/host firewall basics, and backup
  and restore guidance.

The Azure section is documentation only. It emphasizes persistent storage
for both SQLite and the profile snapshot, one VM/worker for this SQLite
design, and keeping port 8000 private behind HTTPS. No credentials or real
career details were added.

## Verification

- **Complete suite:** `python -m pytest -q` — **49 passed in 10.03s**.
- **Database outage/cache selection:**
  `python -m pytest -q tests/test_app.py -k 'outage or cache'` — **7 passed,
  8 deselected in 1.00s**.
- **Live HTTP smoke check:** Started Uvicorn on `127.0.0.1:8765` with a
  separate local smoke-test SQLite database, a throwaway test-only password
  hash/session key, and a separate smoke cache. Verified public HTML returned
  200, CSS returned 200 with responsive rules, unauthenticated `/admin`
  redirected to login with 303, a login without CSRF was rejected with 403,
  valid login reached the owner dashboard with 200, and a skill could be
  created, edited (reflected publicly), and deleted with persisted changes.
- **First smoke attempt:** The harness initially expected the dashboard text
  `Admin dashboard`; the actual page title is `Owner dashboard`. Checked the
  template, corrected only that smoke assertion, and reran the complete smoke
  flow successfully. This was a harness expectation mismatch, not an app
  regression.
- **Cleanup:** Stopped the smoke server and removed its database/cache files.
  The pre-existing `data/public-profile.json` was left untouched.
- **Diff hygiene:** `git diff --check` passed.

The automated admin tests additionally cover configuration requirements,
unauthenticated route protection, valid/invalid login, secure cookie flags,
logout, CSRF rejection, validation, and create/edit/delete for each content
type. The outage tests confirm the public page renders the saved snapshot or
bundled fallback while database reads fail.

## Result and remaining concerns

No blocking app regression was found, so no runtime code changes were needed.
The work is limited to README/report documentation. Azure readiness is
documented but has not been validated against a provisioned VM, reverse proxy,
firewall, or backup service; those remain future deployment tasks. SQLite is
intended for one VM and one worker, not horizontally scaled app instances.
Nothing was pushed to GitHub.

### Documentation finding fix

Updated the README wording from “pinned project requirements” to
“version-constrained project requirements” to accurately describe dependency
version ranges.

### Public skills ordering fix

Removed the alphabetical sort from the public profile Skills section so skills
follow the profile relationship's configured `display_order`. Added a regression
test using skill names that sort differently alphabetically and by configured
order; it also confirms nested experience skill ordering remains unchanged.
The regression test failed before the template fix as expected. Focused public
page tests (`python -m pytest -q tests/test_app.py`) passed (16 tests), and the
full suite (`python -m pytest -q`) passed (50 tests).
