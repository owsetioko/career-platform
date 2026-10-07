# Azure VM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Personal Resume Platform on the Azure VM `vm-career-platform`, serving Chris's real profile data from SQLite.

**Architecture:** One Ubuntu 24.04 VM, reached only over SSH from the laptop. The app is cloned from GitHub, installed into a uv-managed virtual environment from a pinned lock file, and run by Uvicorn bound to `127.0.0.1:8000`, so it is never exposed to the internet. The SQLite database is built on the laptop from `data/resume-seed.sql` and copied to the VM with `scp`. Chris views the site through an SSH tunnel.

**Tech Stack:** Azure VM (Ubuntu Server 24.04 LTS, x64), apt, git, sqlite3, uv, Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite.

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

1. **There is no lock file in the repo yet.** The repo has only `requirements.txt` (version ranges), with no `pyproject.toml` or `uv.lock`, so a literal `uv sync` has nothing to read. The **Python** section first creates `requirements.lock` on the laptop with `uv pip compile` and commits it. The VM then runs `uv pip sync requirements.lock`, which is the requirements-file equivalent of `uv sync`: it installs exactly the pinned versions and nothing else. *If you'd rather not change the repo, replace Python steps 1–3 with `uv pip install -r requirements.txt` on the VM. Versions are then not pinned.*
2. **There was no existing database.** It is built on the laptop from `data/resume-seed.sql` (created from the September 6, 2026 self-discovery interview, public facts only). This happens in **Data** step 1, then the `.db` file is copied with `scp`, as in the outline.
3. **Uvicorn runs in the background with `nohup`**, as the outline says ("start uvicorn"). The README's `systemd` service, dedicated service account, HTTPS proxy and backups are out of scope. They're listed at the end as follow-ups.

## Review Focus

These are the most likely ways this migration can look like it worked when it didn't:

1. **Uvicorn started from the wrong folder.** `DATABASE_URL=sqlite:///./data/resume.db` is *relative to the current directory*. Started anywhere other than `~/career-platform`, the app silently creates a new, empty database and shows "Your Name". Covered by Processes step 1 (`cd` first) and Verify step 1 (look for "Chris Setioko").
2. **The page renders from the fallback, not the database.** If SQLite can't be read, the app still serves a page from `data/public-profile.json` or the bundled starter profile. Verify step 2 confirms the database was read: the snapshot file is written only after a successful database read, and it must contain your name.
3. **The VM was auto-shut-down at 6 PM.** SSH times out and nothing is running. Covered by Server step 1 (check power state first) and the note in Processes.
4. **Your laptop's IP changed** (campus Wi-Fi, hotspot). SSH times out even though the VM is running. Covered by Server step 2.
5. **Personal data leaks into the public repo.** `data/` and `.env` are git-ignored, but `git add -A` after the lock-file step could still catch something unexpected. Covered by Python step 2 (add the lock file by name and check `git status`).

---

## Server: Azure VM, already created, reached over SSH

- [ ] **Step 1: Make sure the VM is running**
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

- [ ] **Step 2: Confirm the SSH firewall rule still matches your laptop's IP**
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

- [ ] **Step 3: Open an SSH session**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    ssh -i ~/.ssh/isba4775_azure azureuser@"$VM_IP"
    ```
  - **Why:** Every `VM` step below runs inside this session.
  - **Check:** The prompt becomes `azureuser@vm-career-platform:~$`, and `lsb_release -ds` prints `Ubuntu 24.04.x LTS`.
  - **Undo:** `exit` closes the session.

## Packages: apt-get: git, sqlite3

- [ ] **Step 1: Record what's already installed**
  - **Where:** VM
  - **Run:**
    ```bash
    dpkg-query -W -f='${Package} ${Status}\n' git sqlite3 2>&1 | tee ~/packages-before.txt
    ```
  - **Why:** Ubuntu's cloud image already includes `git`. This record tells the Undo step which package *we* added, so it doesn't remove one the system came with.
  - **Check:** `~/packages-before.txt` exists, with one line per package (or a "no packages found" line).
  - **Undo:** `rm ~/packages-before.txt`

- [ ] **Step 2: Install git and sqlite3**
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

## Code: git clone from GitHub

> The Python section adds a commit (the lock file) on the laptop first. You can clone now and `git pull` later, as shown in Python step 4.

- [ ] **Step 1: Clone the repository**
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

## Python: uv, then uv sync from the lock file

- [ ] **Step 1: Install uv on the laptop and generate the lock file**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    brew install uv
    cd ~/Desktop/career-platform
    uv pip compile requirements.txt --universal --python-version 3.12 -o requirements.lock
    ```
  - **Why:** Turns the version *ranges* in `requirements.txt` into exact pins that work on both macOS and Linux (`--universal`). The laptop and the VM then install identical versions.
  - **Check:** `head -5 requirements.lock` shows a uv header, and `grep -E '^(fastapi|uvicorn|sqlalchemy)==' requirements.lock` prints three pinned lines.
  - **Undo:** `rm requirements.lock` (and `brew uninstall uv`).

- [ ] **Step 2: Commit and push only the lock file**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    git add requirements.lock
    git status --short
    git commit -m "build: add uv lock file for deployments"
    git push origin main
    ```
  - **Why:** The VM gets code only from GitHub, so the lock file has to be pushed.
  - **Check:** `git status --short`, run before committing, shows **only** `A  requirements.lock`, with nothing from `data/` and no `.env`. After pushing, `git status` says `up to date with 'origin/main'`.
  - **Undo:** `git revert HEAD && git push origin main`

- [ ] **Step 3: Install uv on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.local/bin/env
    ```
  - **Why:** uv creates the virtual environment and installs from the lock file. It installs into `~/.local/bin` for `azureuser` only, without `sudo`.
  - **Check:** `uv --version` prints `uv 0.x.y`.
  - **Undo:** `rm -f ~/.local/bin/uv ~/.local/bin/uvx && rm -rf ~/.cache/uv ~/.local/share/uv`

- [ ] **Step 4: Pull the lock file onto the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform && git pull
    ```
  - **Why:** The clone in the Code section may predate the lock-file commit.
  - **Check:** `ls requirements.lock` succeeds, and `git log -1 --oneline` shows `build: add uv lock file for deployments`.
  - **Undo:** `git reset --hard HEAD~1` (local only; this doesn't affect GitHub).

- [ ] **Step 5: Create the virtual environment and sync from the lock file**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    uv venv --python 3.12
    uv pip sync requirements.lock
    ```
  - **Why:** `uv pip sync` installs exactly what the lock file lists and removes anything else, which is what `uv sync` does for a uv project.
  - **Check:**
    ```bash
    .venv/bin/python --version     # Python 3.12.x
    uv pip check                   # "All installed packages are compatible"
    .venv/bin/python -c "import fastapi, uvicorn, sqlalchemy, argon2, jinja2; print('ok')"   # ok
    ```
  - **Undo:** `rm -rf ~/career-platform/.venv`

## Config: copy .env from .env.example

- [ ] **Step 1: Create `.env` on the VM**
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

## Data: scp my SQLite .db file from my laptop

- [ ] **Step 1: Build `data/resume.db` on the laptop from the seed file**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    cd ~/Desktop/career-platform
    uv venv --python 3.12
    uv pip sync requirements.lock
    .venv/bin/python -m app.database
    sqlite3 data/resume.db < data/resume-seed.sql
    ```
  - **Why:** `python -m app.database` creates the tables with the app's own schema code. The seed file then fills in your profile, skills, projects, job and education. It's written in SQL so you can read and edit it, and it's safe to run again.
  - **Check:**
    ```bash
    sqlite3 data/resume.db "SELECT display_name, headline FROM profiles WHERE slug='owner';"
    # Chris Setioko|Information Systems & Business Analytics Senior
    sqlite3 data/resume.db "SELECT (SELECT count(*) FROM skills), (SELECT count(*) FROM projects), (SELECT count(*) FROM experiences), (SELECT count(*) FROM education);"
    # 7|3|1|1
    git check-ignore data/resume.db    # prints data/resume.db, so Git will never commit it
    ```
  - **Undo:** `rm data/resume.db` (the seed file stays; rebuild with the same commands).

- [ ] **Step 2: Create the data folder on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    mkdir -p ~/career-platform/data
    chmod 700 ~/career-platform/data
    ```
  - **Why:** `scp` needs the target folder to exist. `700` keeps the database and profile snapshot private to `azureuser`.
  - **Check:** `ls -ld ~/career-platform/data` shows `drwx------`.
  - **Undo:** `rmdir ~/career-platform/data` (only while it's empty).

- [ ] **Step 3: Copy the database to the VM**
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

- [ ] **Step 4: Confirm the app can open the copied database**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    .venv/bin/python -m app.database
    sqlite3 data/resume.db "SELECT display_name FROM profiles WHERE slug='owner';"
    ```
  - **Why:** `app.database` is the README's safe schema check. It adds missing tables or columns and never duplicates the profile. It proves the VM's Python can open the file with the app's settings.
  - **Check:** No error, and the query prints `Chris Setioko` (not `Your Name`).
  - **Undo:** Repeat Data step 3 to overwrite it with the laptop copy.

## Processes: start uvicorn

- [ ] **Step 1: Start Uvicorn in the background, bound to localhost**
  - **Where:** VM
  - **Run:**
    ```bash
    cd ~/career-platform
    nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 &
    echo $! > ~/uvicorn.pid
    ```
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

## Verify: the site answers on the VM and shows my data

- [ ] **Step 1: The site answers on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/static/css/styles.css
    curl -s http://127.0.0.1:8000/ | grep -o "Chris Setioko" | head -1
    curl -s http://127.0.0.1:8000/ | grep -c "Your Name"
    ```
  - **Why:** Shows the page and stylesheet load, and that the page shows your data, not the starter placeholder.
  - **Check:** `200`, `200`, `Chris Setioko`, `0`.
  - **Undo:** Nothing to undo (read-only).

- [ ] **Step 2: Prove the page came from the database, not the fallback**
  - **Where:** VM
  - **Run:**
    ```bash
    ls -l ~/career-platform/data/public-profile.json
    grep -o '"display_name": *"[^"]*"' ~/career-platform/data/public-profile.json
    grep -iE "error|traceback" ~/uvicorn.log || echo "no errors"
    ```
  - **Why:** The app writes `public-profile.json` only after a **successful** database read. If it exists and contains your name, the data came from SQLite (Review Focus #2).
  - **Check:** The file exists with a fresh timestamp, the grep prints `"display_name": "Chris Setioko"`, and the log check prints `no errors`.
  - **Undo:** Nothing to undo (the snapshot is meant to stay; it's the app's safety net).

- [ ] **Step 3: See it in your own browser through an SSH tunnel**
  - **Where:** LAPTOP (new Terminal tab)
  - **Run:**
    ```bash
    ssh -i ~/.ssh/isba4775_azure -N -L 8000:127.0.0.1:8000 azureuser@"$VM_IP"
    ```
    Leave it running, then open **http://127.0.0.1:8000** in your browser.
  - **Why:** Lets you view the site without opening any port on Azure. The tunnel carries browser traffic over SSH to the VM's localhost.
  - **Check:** The page shows "Chris Setioko", your headline, the three projects, the skills list, and LMU under education, with the styling applied.
  - **Undo:** Press **Ctrl+C** in that tab to close the tunnel.

---

## Out of scope: follow-ups after this plan

- Run Uvicorn as a `systemd` service under a dedicated account so it starts on boot (README → *Service startup and recovery*).
- Add Nginx or Caddy with HTTPS, then open port 443 in the firewall so the public can reach the site (README → *HTTPS, proxy, and network*).
- Enable admin: generate `ADMIN_PASSWORD_HASH` and `SESSION_SECRET` and set `SESSION_COOKIE_SECURE=true` once HTTPS is in place.
- Back up `data/resume.db` and `data/public-profile.json` off the VM (README → *Backups and restore*).
- Before deleting the whole deployment: `az group delete -n rg-career-platform` also removes the public IP, which isn't set to be deleted with the VM.
