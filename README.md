# Personal Resume Platform

A Codespaces-first personal resume site built with FastAPI, Jinja2, SQLite,
and plain CSS. The public page can use a saved profile snapshot if SQLite is
temporarily unavailable. An optional password-protected admin area lets the
owner edit the profile and its experience, skills, projects, and education.

## Start in GitHub Codespaces

1. Open this repository in a Codespace and wait for the workspace to finish
   starting.
2. Open **Terminal → New Terminal**.
3. Create a Python virtual environment, install the dependencies, and create
   your local settings file:

   ```bash
   python --version
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements-dev.txt
   cp .env.example .env
   ```

   The app supports Python 3.10 or newer. Keep the virtual environment
   activated in each terminal where you run the app or tests.
4. Create the SQLite tables and starter profile:

   ```bash
   python -m app.database
   ```

   You can safely run this command again after an app update; it creates
   missing tables/columns and does not duplicate the starter profile. The
   default database is `data/resume.db`. The `data/` directory is ignored by
   Git, so your database and profile snapshot are not committed.
5. Start the development server:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. In Codespaces, open the **Ports** panel and follow the link for port 8000.
   The first page uses clearly marked starter-profile placeholders. Replace
   them in the admin area before sharing your site. Stop the server with
   **Ctrl+C** in the terminal.

To run outside Codespaces, use the same commands and open
`http://127.0.0.1:8000` in your browser. The environment file is named `.env`;
it is intentionally excluded from Git. `.env.example` documents the basic
settings:

```dotenv
APP_TITLE=Personal Resume Platform
DATABASE_URL=sqlite:///./data/resume.db
```

`DATABASE_URL` is a SQLAlchemy database URL. Leave the example value for the
default local SQLite file, or change it to another SQLite path if needed. This
app's deployment guidance below assumes SQLite on one VM; it is not a
multi-instance database setup.

## Configure the owner admin

Admin is disabled until both an Argon2id password hash and a session-signing
secret are configured. The public page still works when admin is disabled.
Do not put a plain-text password in `.env`, and never commit `.env` or copy
real secrets into this README.

1. In an activated virtual environment, create a password hash. The prompt
   does not echo the password:

   ```bash
   python -c 'from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass("Admin password: ")))'
   ```

2. Generate a separate random session secret:

   ```bash
   python -c 'import secrets; print(secrets.token_urlsafe(48))'
   ```

3. Open `.env` in the Codespaces editor or a terminal editor such as `nano .env`.
   Add both generated values:

   ```dotenv
   ADMIN_PASSWORD_HASH=paste-the-generated-argon2id-hash-here
   SESSION_SECRET=paste-the-generated-session-secret-here
   ```

   The session secret must be at least 32 bytes. Keep `.env` private and
   untracked; on a hosted machine use a root-readable deployment environment
   file or a secret manager instead.
4. Set the cookie option to match the URL you use:

   ```dotenv
   SESSION_COOKIE_SECURE=false
   ```

   Use `false` only for plain-HTTP local development. If you access the app
   over HTTPS—including an HTTPS Codespaces forwarded port—set it to `true`.
   Restart the server after changing `.env`.
5. Visit `/admin/login`, sign in, and use the dashboard to update the profile
   and manage content. Every admin page requires authentication. Forms include
   CSRF protection; cookies are HttpOnly and SameSite=Lax. Content items can
   be hidden or assigned a display order.

## Database, public page, and tests

The owner profile has the slug `owner` and is created by
`python -m app.database`. The public page reads the profile and visible
content from SQLite. It is served at `/`; the stylesheet is at
`/static/css/styles.css`.

After a successful database read, the app refreshes
`data/public-profile.json` as a last-known-good public snapshot. If a database
read fails, the page uses that snapshot, or the bundled starter profile if
there is no usable snapshot. The fallback keeps the public page readable; it
does not make admin edits available while the database is down. Protect and
back up both the database and snapshot in a deployment.

Run all tests from the repository root with the virtual environment active:

```bash
python -m pytest
```

Tests use isolated temporary databases and do not require real profile data or
admin credentials.

## Troubleshooting

- **`ModuleNotFoundError` or missing package:** activate `.venv` and run
  `python -m pip install -r requirements-dev.txt` again.
- **The page cannot find the database or profile:** stop the server, run
  `python -m app.database` from the repository root, then restart it. The
  initializer creates the parent directory for a configured SQLite file.
- **Port 8000 is already in use:** stop the other server, or choose another
  port in the `uvicorn` command and open that port in Codespaces.
- **`/admin` says admin is not configured:** check that `.env` contains both
  `ADMIN_PASSWORD_HASH` (a valid Argon2id hash) and a `SESSION_SECRET` of at
  least 32 bytes, then restart the app. Do not paste the plaintext password
  as the hash.
- **Admin login succeeds but pages keep returning to login:** clear the
  browser's `resume_session` cookie, confirm the app URL uses the expected
  HTTP/HTTPS setting for `SESSION_COOKIE_SECURE`, and sign in again.
- **The public page shows a temporary database warning:** verify that the
  configured database file exists and that the app's operating-system user
  can read and write its directory. The snapshot or bundled starter profile
  may still render while you restore database access.
- **Local changes are not showing:** confirm you edited the `owner` profile
  in `/admin`, saved the form, and left the content item visible. A hidden
  item is intentionally omitted from the public page.

## Future Azure Linux VM readiness (guidance only)

These notes describe a possible later single-VM setup; they do not create Azure
resources or deploy the app. Plan to use a supported Linux VM, install a
maintained Python 3.10+ runtime, and install the pinned project requirements
into a virtual environment. Keep the deployment code separate from the
persistent data disk, and test upgrades and restores before relying on the
site.

### Persistent files and secrets

- Put `resume.db` and `public-profile.json` on persistent, backed-up storage.
  The app expects the snapshot at `<app-directory>/data/public-profile.json`;
  a simple layout is a separately mounted Azure managed data disk mounted at
  `<app-directory>/data`. Mount it by a stable disk identifier in the VM's
  boot-time mount configuration, not by an unstable device name. Confirm the
  disk is mounted before starting the app, and set directory ownership and
  permissions so only the service account can write there. Do not keep the
  only copy on an OS temporary/ephemeral disk.
- Alternatively, set `DATABASE_URL` to a SQLite file on persistent storage.
  The profile snapshot still lives in the app's `data/` directory, so protect
  that directory too. For example, an absolute SQLite path such as
  `/var/lib/personal-resume-platform/resume.db` is written as
  `sqlite:////var/lib/personal-resume-platform/resume.db`.
- This SQLite design is for one VM and one app worker, not multiple app
  instances sharing a database file. Keep a stable app path or explicitly
  move both persistent data paths before upgrading the code.
- Set `ADMIN_PASSWORD_HASH`, `SESSION_SECRET`, `DATABASE_URL`, and
  `SESSION_COOKIE_SECURE=true` in the service environment. Generate a unique,
  random session secret and a strong admin password hash for the deployment;
  never reuse development values or commit any secrets. Store secrets in an
  appropriately protected secret manager or a root-owned environment file
  (for example, mode `600`); do not put them in shell history or a
  world-readable file. Restrict access to backups because they contain the
  public profile and database.

### Service startup and recovery

Run Uvicorn under a dedicated, non-login service account and a process
supervisor such as `systemd`, rather than leaving it in an interactive SSH
terminal. A unit should use the app directory as its working directory, load
the protected environment file, bind Uvicorn to `127.0.0.1:8000`, and restart
on failure. For example, after creating the service account, app directory,
virtual environment, and protected environment file, a unit at
`/etc/systemd/system/personal-resume-platform.service` could contain:

```ini
[Unit]
Description=Personal Resume Platform
After=network.target

[Service]
User=personal-resume-platform
Group=personal-resume-platform
WorkingDirectory=/opt/personal-resume-platform
EnvironmentFile=/etc/personal-resume-platform.env
ExecStart=/opt/personal-resume-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=multi-user.target
```

Adjust the paths and account to match the VM, and make sure that account can
read the app and write to the persistent data directory. A typical operator
workflow after creating and reviewing the unit is:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now personal-resume-platform
sudo systemctl status personal-resume-platform
sudo journalctl -u personal-resume-platform
```

Initialize or upgrade the schema deliberately with the deployment's virtual
environment before bringing the service back up:
`<app-directory>/.venv/bin/python -m app.database`. Check the service logs and
the public page after a restart. To restart after changing app code or
environment settings, run
`sudo systemctl restart personal-resume-platform`; after editing the unit,
run `sudo systemctl daemon-reload` first. Ensure the persistent disk is
mounted and writable before running initialization or starting the service.

### HTTPS, proxy, and network

Put a maintained reverse proxy such as Nginx or Caddy in front of Uvicorn and
configure HTTPS with a valid certificate. Configure the proxy to pass the
original host and HTTPS scheme, and configure Uvicorn to trust forwarded
headers only from that local proxy. Do not make port 8000 publicly reachable.
With HTTPS enabled, `SESSION_COOKIE_SECURE=true`; this keeps the admin session
cookie restricted to secure connections.

At the Azure network security group and VM firewall, allow inbound HTTPS
(TCP 443) for visitors, and allow HTTP (TCP 80) only if it is needed to
redirect to HTTPS or complete certificate renewal. Restrict SSH (TCP 22) to
trusted administrator addresses or an approved management path; use
key-based access. Do not expose the SQLite file or database ports to the
internet. Keep OS packages, Python dependencies, and the proxy updated.

### Backups and restore

Back up the SQLite database and profile snapshot on a schedule to storage
separate from the VM/data disk, with encryption, access controls, and a
retention policy. Use SQLite's supported online backup mechanism or stop the
service for a consistent file copy; copying only a live `.db` file can miss
uncheckpointed journal/WAL data. Include the snapshot in the same backup
plan, and consider Azure managed-disk backup/snapshots as an additional
recovery layer rather than the only off-machine backup. Periodically test
restoring both files to a separate location and verify the app and profile
before depending on the backups.
