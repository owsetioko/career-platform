# Azure VM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Personal Resume Platform on the Azure VM `vm-career-platform`, serving Chris's real profile data from SQLite.

**Architecture:** One Ubuntu 24.04 VM, reached only over SSH from the laptop. The app is cloned from GitHub, installed into a uv-managed virtual environment from a pinned lock file, and run by Uvicorn bound to `127.0.0.1:8000`, so it is never exposed to the internet. The SQLite database is built on the laptop from `data/resume-seed.sql` and copied to the VM with `scp`. Chris views the site through an SSH tunnel.

**Tech Stack:** Azure VM (Ubuntu Server 24.04 LTS, x64), apt, git, sqlite3, uv, Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite.

**Status:** Run on 2026-10-07. Every step below is ticked and has a **Result** line with what actually happened. The Verify results table is at the end.

**Spec:** Chris's migration outline (below) plus the deployment notes in `README.md` and the app spec in `docs/specs/personal-resume-platform-spec.md`.

```
Server     Azure VM, already created, reached over SSH
Packages   apt-get: git, sqlite3
Code       git clone from GitHub
Python     uv, then uv sync from the lock file
Config     copy .env from .env.example
Data       scp my SQLite .db file from my laptop
Processes  start uvicorn
Verify     the site answers on the VM and shows my data
```

## How to read each step

Every step lists:

- **Where:** `LAPTOP` (macOS Terminal in `~/Desktop/career-platform`), `VM` (inside an SSH session as `azureuser`), or `PORTAL` (portal.azure.com, or the equivalent `az` command on the laptop).
- **Run:** the exact commands, or what to click.
- **Why:** what the step is for.
- **Check:** how to prove it worked, with the expected output.
- **Undo:** how to reverse it.

Run the steps in order. If a **Check** doesn't match, stop. Don't continue to the next step.

## Global Constraints

- VM: `vm-career-platform`, resource group `rg-career-platform`, region North Central US, size `Standard_B2ats_v2`.
- Public IP: not written here, because this repo is public. It is a static Standard SKU address that survives stop/start. Before running any `LAPTOP` step that connects to the VM, set it in that terminal:
  ```bash
  VM_IP=$(az vm show -d -g rg-career-platform -n vm-career-platform --query publicIps -o tsv)
  ```
- SSH user and key, always: `ssh -i ~/.ssh/isba4775_azure azureuser@"$VM_IP"`.
- The firewall rule `AllowSSHFromLaptop` allows port 22 only from your laptop's current public IP (a single `/32` address). No other inbound port is open, and this plan opens none.
- Uvicorn binds to `127.0.0.1:8000` only. Do **not** add a firewall rule for port 8000.
- Never commit `.env` or anything in `data/`. The GitHub repo `owsetioko/career-platform` is **public**.
- App directory on the VM: `/home/azureuser/career-platform` (written `~/career-platform`).
- Python: 3.12 (Ubuntu 24.04's default; the app needs 3.10 or newer).
- Auto-shutdown deallocates the VM daily at **6:00 PM Pacific**. Anything started by hand (Uvicorn) is gone after that.

## Decisions made while writing this plan

1. **There was no lock file in the repo.** The repo had only `requirements.txt` (version ranges), with no `pyproject.toml` or `uv.lock`, so a literal `uv sync` had nothing to read. *As run:* the **Python** section adds a `pyproject.toml` that mirrors `requirements.txt` (runtime) and `requirements-dev.txt` (a `dev` group), creates `uv.lock` with `uv lock`, and commits both. The VM then runs `uv sync --locked --no-dev`. (This plan first proposed a `requirements.lock` from `uv pip compile`; it was replaced before the Python section ran.)
2. **There was no existing database.** It is built on the laptop from `data/resume-seed.sql` (written from Chris's resume plus the September 6, 2026 self-discovery interview, public facts only). This happens in **Data** step 1, then the `.db` file is copied with `scp`, as in the outline.
3. **Uvicorn runs in the background with `nohup`**, as the outline says ("start uvicorn"). The README's `systemd` service, dedicated service account, HTTPS proxy and backups are out of scope. They're listed at the end as follow-ups.

## Review Focus

These are the most likely ways this migration can look like it worked when it didn't:

1. **Uvicorn started from the wrong folder.** `DATABASE_URL=sqlite:///./data/resume.db` is *relative to the current directory*. Started anywhere other than `~/career-platform`, the app silently creates a new, empty database and shows "Your Name". Covered by Processes step 1 (`cd` first) and Verify step 1 (look for "Chris Owen Setioko").
2. **The page renders from the fallback, not the database.** If SQLite can't be read, the app still serves a page from `data/public-profile.json` or the bundled starter profile. Verify step 2 confirms the database was read: the snapshot file is written only after a successful database read, and it must contain your name.
3. **The VM was auto-shut-down at 6 PM.** SSH times out and nothing is running. Covered by Server step 1 (check power state first) and the note in Processes.
4. **Your laptop's IP changed** (campus Wi-Fi, hotspot). SSH times out even though the VM is running. Covered by Server step 2.
5. **Personal data leaks into the public repo.** `data/` and `.env` are git-ignored, but `git add -A` after the lock-file step could still catch something unexpected. Covered by Python step 2 (add `pyproject.toml` and `uv.lock` by name and check `git status`).

---

## Server: Azure VM, already created, reached over SSH

- [x] **Step 1: Make sure the VM is running**
  - **Where:** LAPTOP (or PORTAL → Virtual machines → `vm-career-platform` → Overview → Status)
  - **Run:**
    ```bash
    az vm get-instance-view -g rg-career-platform -n vm-career-platform \
      --query "instanceView.statuses[?starts_with(code,'PowerState')].displayStatus" -o tsv
    ```
    If it prints `VM deallocated`, start it (PORTAL: **Start** button):
    ```bash
    az vm start -g rg-career-platform -n vm-career-platform
    ```
  - **Why:** Auto-shutdown deallocates the VM every evening. Every later step needs it running.
  - **Check:** The command prints `VM running`.
  - **Undo:** `az vm deallocate -g rg-career-platform -n vm-career-platform` (stops billing for compute).
  - **Result:** Printed `VM running`; no start needed.

- [x] **Step 2: Confirm the SSH firewall rule still matches your laptop's IP**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    curl -4 -s https://api.ipify.org; echo
    az network nsg rule show -g rg-career-platform --nsg-name vm-career-platformNSG \
      -n AllowSSHFromLaptop --query sourceAddressPrefix -o tsv
    ```
    If the two IPs differ, update the rule to the new one:
    ```bash
    az network nsg rule update -g rg-career-platform --nsg-name vm-career-platformNSG \
      -n AllowSSHFromLaptop --source-address-prefixes "$(curl -4 -s https://api.ipify.org)/32"
    ```
  - **Why:** SSH is allowed only from one IP. On a different network, SSH just hangs.
  - **Check:** Both commands print the same address, the second with `/32` on the end.
  - **Undo:** Run the update again with the address the rule had before.
  - **Result:** The laptop's public IP matched the rule's `/32` source; no update needed.

- [x] **Step 3: Open an SSH session**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    ssh -i ~/.ssh/isba4775_azure azureuser@"$VM_IP"
    ```
  - **Why:** Every `VM` step below runs inside this session.
  - **Check:** The prompt becomes `azureuser@vm-career-platform:~$`, and `lsb_release -ds` prints `Ubuntu 24.04.x LTS`.
  - **Undo:** `exit` closes the session.
  - **Result:** Run as one-shot SSH commands instead of an interactive session (the agent's shell can't hold one open). Printed `azureuser@vm-career-platform` and `Ubuntu 24.04.4 LTS`.

## Packages: apt-get: git, sqlite3

- [x] **Step 1: Record what's already installed**
  - **Where:** VM
  - **Run:**
    ```bash
    dpkg-query -W -f='${Package} ${Status}\n' git sqlite3 2>&1 | tee ~/packages-before.txt
    ```
  - **Why:** Ubuntu's cloud image already includes `git`. This record tells the Undo step which package *we* added, so it doesn't remove one the system came with.
  - **Check:** `~/packages-before.txt` exists, with one line per package (or a "no packages found" line).
  - **Undo:** `rm ~/packages-before.txt`
  - **Result:** `git install ok installed`; `sqlite3` not found. So Undo removes only `sqlite3`.

- [x] **Step 2: Install git and sqlite3**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo apt-get update
    sudo apt-get install -y git sqlite3
    ```
  - **Why:** `git` clones the code. `sqlite3` lets you inspect the database on the VM.
  - **Check:**
    ```bash
    git --version      # git version 2.x
    sqlite3 --version  # 3.x
    ```
  - **Undo:** Remove only the packages that `~/packages-before.txt` did **not** show as `install ok installed`, for example `sudo apt-get remove -y sqlite3`.
  - **Result:** `git version 2.43.0`, `sqlite3 3.45.1`. Run non-interactively (`DEBIAN_FRONTEND=noninteractive`, `-qq`); log in `/tmp/apt-install.log` on the VM.

## Code: git clone from GitHub

> The Python section adds a commit (`pyproject.toml` + `uv.lock`) on the laptop. You can clone now and `git pull` later, as shown in Python step 4.

- [x] **Step 1: Clone the repository**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~
    git clone https://github.com/owsetioko/career-platform.git
    cd ~/career-platform
    ```
  - **Why:** Puts the app code on the VM. The repo is public, so you don't need a GitHub login on the VM.
  - **Check:**
    ```bash
    git -C ~/career-platform log -1 --oneline
    ls ~/career-platform/app/main.py
    ```
    The commit matches `git log -1 --oneline` on the laptop, and `app/main.py` exists.
  - **Undo:** `rm -rf ~/career-platform`
  - **Result:** VM and laptop both at `3432740`; `app/main.py` present. Cloned before the lock-file commit, which Python step 4 pulled in.

## Python: uv, then uv sync from the lock file

- [x] **Step 1: Install uv on the laptop and create `pyproject.toml` + `uv.lock`**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    brew install uv
    cd ~/Desktop/career-platform
    # pyproject.toml lists the same ranges as requirements.txt, with
    # requirements-dev.txt's extras in a `dev` dependency group and
    # [tool.uv] package = false (an app, not a library).
    uv lock
    ```
  - **Why:** `uv lock` turns the version *ranges* into exact pins for every platform, so the laptop and the VM install identical versions.
  - **Check:**
    ```bash
    uv lock --check                                   # lock matches pyproject.toml
    uv sync --locked --python 3.12
    uv run --locked python -m pytest -q               # all tests pass
    ```
    Use `python -m pytest`, not bare `pytest`: bare `pytest` can't import `app`.
  - **Undo:** `rm pyproject.toml uv.lock && rm -rf .venv` (and `brew uninstall uv`).
  - **Result:** uv 0.12.23. `uv lock` resolved 42 packages (fastapi 0.119.1, uvicorn 0.54.0, SQLAlchemy 2.1.3 on Python 3.11+). `uv lock --check` clean; 50/50 tests passed on Python 3.12.15.

- [x] **Step 2: Commit and push only `pyproject.toml` and `uv.lock`**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    git add pyproject.toml uv.lock
    git status --short
    git commit -m "build: add pyproject.toml and uv.lock for uv-based installs"
    git push origin main
    ```
  - **Why:** The VM gets code only from GitHub, so the lock file has to be pushed.
  - **Check:** `git status --short`, run before committing, shows `A` only next to `pyproject.toml` and `uv.lock`, with nothing from `data/` and no `.env`. After pushing, `git status -sb` shows `main...origin/main` with nothing ahead.
  - **Undo:** `git revert <commit> && git push origin main`
  - **Result:** Commit `ab222f3` contained only those two files; pushed, `main...origin/main` in sync.

- [x] **Step 3: Install uv on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.local/bin/env
    ```
  - **Why:** uv creates the virtual environment and installs from the lock file. It installs into `~/.local/bin` for `azureuser` only, without `sudo`.
  - **Check:** `uv --version` prints `uv 0.x.y`.
  - **Undo:** `rm -f ~/.local/bin/uv ~/.local/bin/uvx && rm -rf ~/.cache/uv ~/.local/share/uv`
  - **Result:** `uv 0.12.23 (x86_64-unknown-linux-gnu)`.

- [x] **Step 4: Pull the lock file onto the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform && git pull
    ```
  - **Why:** The clone in the Code section predates the lock-file commit.
  - **Check:** `ls uv.lock` succeeds, and `git log -1 --oneline` shows `build: add pyproject.toml and uv.lock for uv-based installs`.
  - **Undo:** `git reset --hard HEAD~1` (local only; this doesn't affect GitHub).
  - **Result:** `ab222f3 build: add pyproject.toml and uv.lock for uv-based installs`; `uv.lock` present.

- [x] **Step 5: Create the virtual environment and sync from the lock file**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    uv sync --locked --no-dev --python 3.12
    ```
  - **Why:** `--locked` refuses to run if `uv.lock` doesn't match `pyproject.toml`, and installs exactly the pinned versions. `--no-dev` leaves out pytest and httpx, which a server doesn't need.
  - **Check:**
    ```bash
    .venv/bin/python --version     # Python 3.12.x
    uv pip check                   # "All installed packages are compatible"
    .venv/bin/python -c "import fastapi, uvicorn, sqlalchemy, argon2, jinja2; print('ok')"   # ok
    ```
  - **Undo:** `rm -rf ~/career-platform/.venv`
  - **Result:** Python 3.12.3; 27 packages (no dev group); `All installed packages are compatible`; imports ok (SQLAlchemy 2.1.3, FastAPI 0.119.1).

## Config: copy .env from .env.example

- [x] **Step 1: Create `.env` on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    cp .env.example .env
    chmod 600 .env
    ```
  - **Why:** The app reads `APP_TITLE` and `DATABASE_URL` from `.env`. Mode `600` makes it readable only by `azureuser`, which matters once secrets are added later.
  - **Check:**
    ```bash
    cat .env
    # APP_TITLE=Personal Resume Platform
    # DATABASE_URL=sqlite:///./data/resume.db
    ls -l .env    # -rw------- 1 azureuser azureuser ...
    ```
  - **Undo:** `rm ~/career-platform/.env`

  > With no `ADMIN_PASSWORD_HASH` or `SESSION_SECRET`, **the admin area stays disabled**. That's expected here; the public page works without it. See the follow-ups at the end.
  - **Result:** Contents matched `.env.example`; `-rw-------`; `git check-ignore` confirms it's ignored.

## Data: scp my SQLite .db file from my laptop

- [x] **Step 1: Build `data/resume.db` on the laptop from the seed file**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    cd ~/Desktop/career-platform
    uv run --locked python -m app.database
    sqlite3 data/resume.db < data/resume-seed.sql
    ```
  - **Why:** `python -m app.database` creates the tables with the app's own schema code. The seed file then fills in your profile, skills, projects, jobs and education. It's written in SQL so you can read and edit it, and it's safe to run again.
  - **Check:**
    ```bash
    sqlite3 data/resume.db "SELECT display_name, headline FROM profiles WHERE slug='owner';"
    # Chris Owen Setioko|Information Systems & Business Analytics Student, Loyola Marymount University
    sqlite3 data/resume.db "SELECT (SELECT count(*) FROM skills), (SELECT count(*) FROM projects), (SELECT count(*) FROM experiences), (SELECT count(*) FROM education);"
    # 15|3|5|3
    git check-ignore data/resume.db    # prints data/resume.db, so Git will never commit it
    ```
  - **Undo:** `rm data/resume.db` (the seed file stays; rebuild with the same commands).
  - **Result:** `Chris Owen Setioko|Information Systems & Business Analytics Student, Loyola Marymount University`; counts `15|3|5|3`; `git check-ignore` prints `data/resume.db`.

- [x] **Step 2: Create the data folder on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    mkdir -p ~/career-platform/data
    chmod 700 ~/career-platform/data
    ```
  - **Why:** `scp` needs the target folder to exist. `700` keeps the database and profile snapshot private to `azureuser`.
  - **Check:** `ls -ld ~/career-platform/data` shows `drwx------`.
  - **Undo:** `rmdir ~/career-platform/data` (only while it's empty).
  - **Result:** `drwx------ azureuser azureuser ~/career-platform/data`.

- [x] **Step 3: Copy the database to the VM**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    cd ~/Desktop/career-platform
    scp -i ~/.ssh/isba4775_azure data/resume.db azureuser@"$VM_IP":career-platform/data/resume.db
    ```
  - **Why:** This is the actual data migration. Nothing on the laptop has the file open, so a plain file copy is consistent.
  - **Check:** The fingerprints match on both sides:
    ```bash
    # LAPTOP
    shasum -a 256 data/resume.db
    # VM
    sha256sum ~/career-platform/data/resume.db
    ```
  - **Undo:** VM: `rm ~/career-platform/data/resume.db`
  - **Result:** SHA-256 `da926cf2f397827699c8386252b3b7e9461b59d8abe87b67a31cc34172274dbd` on both the laptop and the VM.

- [x] **Step 4: Confirm the app can open the copied database**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    .venv/bin/python -m app.database
    sqlite3 data/resume.db "SELECT display_name FROM profiles WHERE slug='owner';"
    ```
  - **Why:** `app.database` is the README's safe schema check. It adds missing tables or columns and never duplicates the profile. It proves the VM's Python can open the file with the app's settings.
  - **Check:** No error, and the query prints `Chris Owen Setioko` (not `Your Name`).
  - **Undo:** Repeat Data step 3 to overwrite it with the laptop copy.
  - **Result:** `app.database` ran without error; query printed `Chris Owen Setioko`.

## Processes: start uvicorn

- [x] **Step 1: Start Uvicorn in the background, bound to localhost**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    setsid nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 < /dev/null &
    sleep 3
    ss -ltnpH "sport = :8000" | grep -o "pid=[0-9]*" | head -1 | cut -d= -f2 > ~/uvicorn.pid
    ```
    The pid comes from the process that holds port 8000. The original `echo $! > ~/uvicorn.pid` saved the pid of a wrapper shell instead, so the Undo below would have left Uvicorn running.
  - **Why:** It must start **from `~/career-platform`**, because the database path is relative (Review Focus #1). `nohup` keeps it running after you close SSH. Binding `127.0.0.1` keeps it off the internet.
  - **Check:**
    ```bash
    ss -ltnp | grep 8000          # LISTEN ... 127.0.0.1:8000 ... uvicorn
    tail -n 5 ~/uvicorn.log       # "Uvicorn running on http://127.0.0.1:8000"
    ```
  - **Undo:**
    ```bash
    kill "$(cat ~/uvicorn.pid)" && rm ~/uvicorn.pid
    ```

  > Uvicorn **won't** come back after the 6 PM auto-shutdown or a reboot. After starting the VM, repeat this step. Running it as a `systemd` service is a follow-up.
  - **Result:** Listening on `127.0.0.1:8000`; log ends `Uvicorn running on http://127.0.0.1:8000`, no errors. Two problems found and fixed: `$!` recorded a wrapper shell's pid, not Uvicorn's (the Run block above now reads the pid from port 8000), and the non-interactive SSH call stayed open until closed (`setsid` and `< /dev/null` above prevent that). Uvicorn kept running throughout.

## Verify: the site answers on the VM and shows my data

- [x] **Step 1: The site answers on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/static/css/styles.css
    curl -s http://127.0.0.1:8000/ | grep -o "Chris Owen Setioko" | head -1
    curl -s http://127.0.0.1:8000/ | grep -c "Your Name"
    ```
  - **Why:** Shows the page and stylesheet load, and that the page shows your data, not the starter placeholder.
  - **Check:** `200`, `200`, `Chris Owen Setioko`, `0`.
  - **Undo:** Nothing to undo (read-only).
  - **Result:** `200`, `200`, `Chris Owen Setioko`, `0`. The page also contained no `None`.

- [x] **Step 2: Prove the page came from the database, not the fallback**
  - **Where:** VM
  - **Run:**
    ```bash
    ls -l ~/career-platform/data/public-profile.json
    grep -o '"display_name": *"[^"]*"' ~/career-platform/data/public-profile.json
    grep -iE "error|traceback" ~/uvicorn.log || echo "no errors"
    ```
  - **Why:** The app writes `public-profile.json` only after a **successful** database read. If it exists and contains your name, the data came from SQLite (Review Focus #2).
  - **Check:** The file exists with a fresh timestamp, the grep prints `"display_name": "Chris Owen Setioko"`, and the log check prints `no errors`.
  - **Undo:** Nothing to undo (the snapshot is meant to stay; it's the app's safety net).
  - **Result:** `public-profile.json` written (4,976 bytes) with `"display_name": "Chris Owen Setioko"`; log check printed `no errors`.

- [x] **Step 3: See it in your own browser through an SSH tunnel**
  - **Where:** LAPTOP (new Terminal tab)
  - **Run:**
    ```bash
    ssh -i ~/.ssh/isba4775_azure -N -L 8000:127.0.0.1:8000 azureuser@"$VM_IP"
    ```
    Leave it running, then open **http://127.0.0.1:8000** in your browser.
  - **Why:** Lets you view the site without opening any port on Azure. The tunnel carries browser traffic over SSH to the VM's localhost.
  - **Check:** The page shows "Chris Owen Setioko", your headline, all five experience entries, the skills list, the three projects, and three schools under education, with the styling applied.
  - **Undo:** Press **Ctrl+C** in that tab to close the tunnel.
  - **Result:** Tunnel opened from the laptop; through it the page returned `200`, the title `Chris Owen Setioko | Information Systems & Business Analytics Student, Loyola Marymount University`, and every section (bakery, OSIS, Santa Monica College, Sekolah Ciputra, Custom PC Builds, Bahasa Indonesia). Tunnel closed afterward.

---

## Verify results

What each check tested, what it showed on 2026-10-07, and how much it proves on its own. "Strong" means the check would fail if the data hadn't moved correctly; "weak" means it would pass even if something were wrong.

| Check | Where | What it showed | Strength | Why |
| --- | --- | --- | --- | --- |
| Database fingerprint, laptop vs VM (Data step 3) | Both | Same SHA-256, `da926cf2…74dbd` | Strong | Byte-for-byte proof the VM has exactly the file built on the laptop |
| Row counts after seeding (Data step 1) | Laptop | `15\|3\|5\|3` (skills, projects, experiences, education) | Strong | Matches the seed file; with the matching fingerprint, the VM has the same rows |
| Owner name in the database (Data step 4) | VM | `Chris Owen Setioko` | Strong | The starter profile only knows `Your Name` |
| Name on the page, no placeholder (Verify step 1) | VM | `Chris Owen Setioko`; 0 × `Your Name`; 0 × `None` | Strong | Only the migrated data contains this name |
| Snapshot written after a database read (Verify step 2) | VM | `public-profile.json` with `"display_name": "Chris Owen Setioko"` | Strong | The app writes it only after a successful SQLite read, so the page didn't come from the fallback |
| Locked environment (Python step 5) | VM | 27 packages from `uv.lock`, `All installed packages are compatible`, imports ok | Strong | `--locked` fails if the lock and `pyproject.toml` disagree |
| Page status `200` (Verify step 1) | VM | `200` | Weak | The fallback page also returns `200` |
| Stylesheet status `200` (Verify step 1) | VM | `200` | Weak | Proves static files are served, nothing about the data |
| Listening address (Processes step 1) | VM | `127.0.0.1:8000` | Medium | Proves the app runs and is private, not that it serves the right data |
| No errors in the log (Verify step 2) | VM | `no errors` | Weak | Absence of errors isn't proof of correct behavior |
| Page through an SSH tunnel (Verify step 3) | Laptop | `200`, correct title, every section present | Medium | End-to-end from the laptop, but a `127.0.0.1` view can't be told apart from a local copy |
| Page at the VM's public IP (guide section 6, two locks) | Laptop | `200` and the resume, with `Temp-HTTP-8000` open and Uvicorn on `0.0.0.0:8000`; screenshot in `docs/evidence/ex03-site.png` | Strong | Only the VM answers at its public address |

**Conclusion:** the data moved intact. The fingerprint, the name on the page, and the snapshot each show it independently. The `200` checks alone wouldn't have.

---

## Out of scope: follow-ups after this plan

- Run Uvicorn as a `systemd` service under a dedicated account so it starts on boot (README → *Service startup and recovery*).
- Add Nginx or Caddy with HTTPS, then open port 443 in the firewall so the public can reach the site (README → *HTTPS, proxy, and network*).
- Enable admin: generate `ADMIN_PASSWORD_HASH` and `SESSION_SECRET` and set `SESSION_COOKIE_SECURE=true` once HTTPS is in place.
- Back up `data/resume.db` and `data/public-profile.json` off the VM (README → *Backups and restore*).
- Before deleting the whole deployment: `az group delete -n rg-career-platform` also removes the public IP, which isn't set to be deleted with the VM.
