# Operate the VM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Visitors reach the site at `http://20.88.61.1`. It starts at boot, comes back after a crash, and doesn't run as root.

**Architecture:** `systemd` (Linux's built-in service manager) runs Uvicorn as a service named `career-platform`, as `azureuser`, with two worker processes on `127.0.0.1:8000`. Nginx listens on port 80 and passes each request to Uvicorn. The internet can reach only port 80 (Nginx) and port 22 (SSH). Port 8000 stays private.

**Tech Stack:** Ubuntu 24.04, systemd, Nginx (from apt), Uvicorn 0.54 (already in `~/career-platform/.venv`), Azure NSG.

**Status:** All tasks run on 2026-10-07 (results under each step). The site is live at `http://20.88.61.1`. Crash and reboot tests are Chris's.

**Spec:** Chris's request of 2026-10-07:

```
- Visitors reach it at http://PUBLIC-IP, with no port number.
- It starts when the VM boots, comes back if it crashes, and one crash
  doesn't take the whole site down.
- Port 8000 stays closed to the Internet, and the app doesn't run as root.
Port 80 rule: Allow-HTTP-80, priority 320 (Chris, in the portal).
Service name: career-platform. Run as azureuser. Use the existing code,
.venv and database in ~/career-platform. No repo changes, no new tests,
no crash/restart tests (Chris runs those).
```

## The VM (found 2026-10-07 with read-only `az` commands)

| | |
| --- | --- |
| VM | `vm-career-platform`, resource group `rg-career-platform`, North Central US |
| Size / OS | `Standard_B2ats_v2` (2 vCPUs, 1 GiB RAM), Ubuntu 24.04 |
| Public IP | `20.88.61.1` (static) |
| SSH | `ssh -i ~/.ssh/isba4775_azure azureuser@20.88.61.1` (key only, passwords disabled) |
| Active network card / firewall | NIC `vm-career-platformVMNic` → NSG **`vm-career-platformNSG`** |
| Its inbound rules today | `AllowSSHFromLaptop` (22, your laptop's IP only, priority 1000); `Allow-HTTP-80` (80, from anywhere, priority **310**) |
| Leftovers, not attached to the VM | NIC `vm-career-platform730`, NSG `vm-career-platform-nsg` (no rules), public IP `vm-career-platform-ip`. Ignore these. They have no effect on the site. |

## How to read each step

- **Where:** `LAPTOP` (macOS Terminal), `VM` (inside an SSH session as `azureuser`), or `PORTAL` (portal.azure.com).
- **Run:** what to type or click. **Why:** what it's for. **Check:** the expected output. **Undo:** how to reverse it.

Run the steps in order. If a **Check** doesn't match, stop there.

## Global Constraints

- The service is named `career-platform` and runs as `azureuser`, never as root.
- It uses `/home/azureuser/career-platform` (code, `.venv`, `.env`, `data/resume.db`) exactly as it is. No `git pull`, no edits to repo files, no new tests.
- Uvicorn binds `127.0.0.1:8000` only. No NSG rule for port 8000.
- Port 80 rule: `Allow-HTTP-80`, priority `320`, on `vm-career-platformNSG`. Chris sets it in the portal.
- No crash, kill or reboot tests in this plan. Chris runs those.

## Decisions

1. **Nginx in front, rather than letting Uvicorn bind port 80 itself.** On Linux, only root can open ports below 1024. Nginx starts as root just long enough to open port 80, then handles requests as the unprivileged `www-data` user. The app itself never touches root, and port 8000 stays on `127.0.0.1`. Nginx is also where HTTPS goes later.
2. **Two Uvicorn workers.** `--workers 2` starts one small supervisor process plus two workers that each serve requests. If one worker crashes, the other keeps serving while the supervisor starts a replacement. If the supervisor itself dies, systemd restarts the whole service (`Restart=always`). The README suggests one worker for SQLite. Two is safe here: the public page only reads the database, and the snapshot file is replaced atomically (`os.replace`), so two workers can't corrupt it.
3. **No separate environment file.** The app loads `~/career-platform/.env` itself, by absolute path. The database path (`./data/resume.db`) is relative, though, so the service **must** start in `~/career-platform`. `WorkingDirectory=` takes care of that.

## Review Focus

The most likely ways this looks done but isn't:

1. **The hand-started Uvicorn is still holding port 8000.** The new service then fails with "address already in use" and keeps retrying. Task 1 stops it, and Task 2's check shows `active (running)`.
2. **Wrong working directory.** The app would create an empty database and show "Your Name". Task 2 sets `WorkingDirectory=`, and Task 5 looks for your name with zero "Your Name".
3. **Nginx's default "Welcome to nginx!" page is still enabled.** Port 80 then answers `200` with the wrong page. Task 3 removes the default site, and Tasks 3 and 5 check for your name on port 80.
4. **The port 80 rule is edited on the wrong NSG, or added as a duplicate.** There are two NSGs, and a rule with that name already exists. Task 4 names the exact NSG and checks with `az`.
5. **Something only works until the 6 PM auto-shutdown.** Both services must be enabled for boot. Tasks 2 and 3 check `systemctl is-enabled`. Your own reboot test is the final proof.

---

### Task 0: Before you start (about 2 min)

- [x] **Step 1: Make sure the VM is running and SSH is allowed from where you are**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    az vm get-instance-view -g rg-career-platform -n vm-career-platform \
      --query "instanceView.statuses[?starts_with(code,'PowerState')].displayStatus" -o tsv
    curl -4 -s https://api.ipify.org; echo
    az network nsg rule show -g rg-career-platform --nsg-name vm-career-platformNSG \
      -n AllowSSHFromLaptop --query sourceAddressPrefix -o tsv
    ```
  - **Why:** Auto-shutdown deallocates the VM at 6 PM, and SSH only works from one IP address.
  - **Check:** `VM running`, then two matching IPs (the second ends in `/32`). If the VM is deallocated, run `az vm start -g rg-career-platform -n vm-career-platform`. If the IPs differ, follow Server step 2 of `2026-09-24-azure-vm-migration.md`.
  - **Undo:** Nothing to undo (read-only).
  - **Result:** Printed `VM running`, so no start was needed. The laptop's public IP matched the rule's `/32` source, so no update was needed.

- [x] **Step 2: Open an SSH session**
  - **Where:** LAPTOP
  - **Run:** `ssh -i ~/.ssh/isba4775_azure azureuser@20.88.61.1`
  - **Check:** The prompt is `azureuser@vm-career-platform:~$`. Every `VM` step below runs here.
  - **Undo:** `exit`
  - **Result:** Run as a one-shot SSH command, because the agent's shell can't hold an interactive session open: `ssh -i ~/.ssh/isba4775_azure azureuser@20.88.61.1 'echo "$(whoami)@$(hostname)"; lsb_release -ds'`. Printed `azureuser@vm-career-platform` and `Ubuntu 24.04.4 LTS`. Key login worked, and no host-key prompt appeared.

### Task 1: Stop the hand-started Uvicorn (about 2 min)

**Why this section:** From now on, systemd owns the app. A copy you started by hand would be holding port 8000, and the service couldn't start.

- [x] **Step 1: Find and stop anything on port 8000**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo ss -ltnp 'sport = :8000'
    pkill -u azureuser -f 'career-platform/.venv/bin/uvicorn' || echo "nothing to stop"
    rm -f ~/uvicorn.pid
    sleep 2
    sudo ss -ltnp 'sport = :8000'
    ```
  - **Why:** The first `ss` shows what's there now. After a 6 PM shutdown, that may be nothing. `pkill` stops only Uvicorn processes from this app's `.venv`.
  - **Check:** The last `ss` prints only its header line, with no `LISTEN` rows.
  - **Undo:** Not needed. Task 2 starts the app again, this time under systemd.
  - **Result:** Nothing was running. The first `ss` showed no listener on 8000, and no process matched. The VM had been shut down since Uvicorn was started by hand. `~/uvicorn.pid` was stale (its pid, 3745, wasn't running) and was removed. `pkill` printed `nothing to stop`, and the final `ss` printed only its header. One change for one-shot SSH: the pattern was written `"[c]areer-platform/.venv/bin/uvicorn"`. Unbracketed, it would also match (and kill) the remote shell running the command, because that shell's own command line contains the pattern. In an interactive session, the plan's original form is fine.

### Task 2: Create the `career-platform` service (about 5 min)

**Why this section:** A systemd *unit file* is a short text file that tells Linux how to run a program. It says which user to run as, which folder to start in, what command to run, what to do if it dies, and whether to start it at boot.

**Produces:** service `career-platform`, Uvicorn on `127.0.0.1:8000`. Task 3 relies on this.

- [x] **Step 1: Write the unit file**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/systemd/system/career-platform.service > /dev/null <<'EOF'
    [Unit]
    Description=Career platform (Uvicorn)
    After=network.target

    [Service]
    User=azureuser
    Group=azureuser
    WorkingDirectory=/home/azureuser/career-platform
    ExecStart=/home/azureuser/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
    Restart=always
    RestartSec=3
    UMask=0077

    [Install]
    WantedBy=multi-user.target
    EOF
    ```
  - **Why, line by line:** `User`/`Group`: not root. `WorkingDirectory`: the database path is relative to this folder. `--host 127.0.0.1`: reachable only from inside the VM. `--workers 2`: one crashed worker doesn't take the site down. `Restart=always` + `RestartSec=3`: if the whole service dies, systemd starts it again 3 seconds later. `UMask=0077`: new files (database journal, snapshot) are private to `azureuser`. `WantedBy=multi-user.target`: start at boot.
  - **Check:** `systemd-analyze verify /etc/systemd/system/career-platform.service` prints nothing.
  - **Undo:** `sudo rm /etc/systemd/system/career-platform.service`
  - **Result:** No unit file existed beforehand. Written exactly as above, with the heredoc sent over SSH as standard input. `systemd-analyze verify` printed nothing (exit 0).

- [x] **Step 2: Load it, enable it for boot, and start it**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable --now career-platform
    ```
  - **Why:** `daemon-reload` makes systemd read the new file. `enable` sets it to start at boot, and `--now` also starts it right away.
  - **Check:**
    ```bash
    systemctl is-enabled career-platform     # enabled
    systemctl is-active career-platform      # active
    sudo ss -ltnp 'sport = :8000'            # LISTEN on 127.0.0.1:8000, not 0.0.0.0
    ps -eo user,pid,ppid,args | grep '[c]areer-platform/.venv'
    curl -s http://127.0.0.1:8000/ | grep -o "Chris Owen Setioko" | head -1
    journalctl -u career-platform -n 20 --no-pager
    ```
    `ps` shows the supervisor plus two workers, every line starting with `azureuser` and none with `root`. Both workers' `ppid` is the supervisor's `pid`. `curl` prints `Chris Owen Setioko`. The log shows `Started worker processes` twice, with no `Traceback`.
  - **Undo:**
    ```bash
    sudo systemctl disable --now career-platform
    sudo rm /etc/systemd/system/career-platform.service
    sudo systemctl daemon-reload
    ```
  - **Result (10:18 UTC):** `enable` created the `multi-user.target.wants` symlink, so it starts at boot. `is-enabled` printed `enabled`, and `is-active` printed `active`. `ss` showed `LISTEN 127.0.0.1:8000` (not `0.0.0.0`), held by the supervisor (pid 1655) and both workers (1662, 1663). The service's processes (read from its cgroup) were 1655 `uvicorn` plus 1661, 1662 and 1663 `python`, all owned by `azureuser` and none by `root`. `curl` printed `200`, `Chris Owen Setioko`, and `0` × `Your Name`. The journal has no `Traceback`.
    Two differences from the expected output above, both mistakes in the plan rather than problems with the service: (1) Uvicorn 0.54 logs `Started parent process [1655]`, then `Started server process` once per worker, not `Started worker processes`. (2) `ps` shows a fourth process, 1661, Python's `multiprocessing.resource_tracker`. It's a housekeeping helper that the worker spawning starts, not a third worker. Its parent is the supervisor, and it runs as `azureuser`.

### Task 3: Put Nginx on port 80 (about 6 min)

**Why this section:** A *reverse proxy* receives visitors' requests and forwards them to the app. Nginx opens port 80 (which needs root), then forwards each request to `127.0.0.1:8000`. Visitors never talk to Uvicorn directly.

**Consumes:** `career-platform` on `127.0.0.1:8000` (Task 2).

- [x] **Step 1: Install Nginx and check the VM's own firewall**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo apt-get update
    sudo apt-get install -y nginx
    sudo ufw status
    ```
  - **Why:** apt installs Nginx and sets it to start at boot. `ufw` is Ubuntu's firewall inside the VM. On Azure images it's normally off.
  - **Check:** `nginx -v` prints `nginx version: nginx/1.24.x`. `ufw` prints `Status: inactive`. If it says `active`, run `sudo ufw allow 80/tcp`.
  - **Undo:** `sudo apt-get purge -y nginx nginx-common && sudo apt-get autoremove -y`
  - **Result (10:31 UTC):** Nginx wasn't installed beforehand. apt ran non-interactively (`DEBIAN_FRONTEND=noninteractive`, `-qq`), exit 0, with its log in `/tmp/nginx-install.log` on the VM. `nginx -v` printed `nginx/1.24.0 (Ubuntu)`, and `ufw` printed `Status: inactive`, so no ufw rule was needed. Nginx was already `enabled` and `active`.

- [x] **Step 2: Replace the default site with one that forwards to the app**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/nginx/sites-available/career-platform > /dev/null <<'EOF'
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    EOF
    sudo ln -s /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
    sudo rm /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl reload nginx
    ```
  - **Why:** `default_server` + `server_name _` answer every request on port 80, whatever address the visitor typed. The `proxy_set_header` lines tell the app the visitor's real address and that the request came in over `http`. (By default, Uvicorn trusts these headers only from `127.0.0.1`, which is Nginx.) Removing `sites-enabled/default` turns off the "Welcome to nginx!" page. The original file stays in `sites-available`.
  - **Check:** `nginx -t` prints `syntax is ok` and `test is successful`. Then:
    ```bash
    curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/            # 200
    curl -s http://127.0.0.1/ | grep -o "Chris Owen Setioko" | head -1    # Chris Owen Setioko
    curl -s http://127.0.0.1/ | grep -c "Welcome to nginx"                # 0
    ```
  - **Undo:**
    ```bash
    sudo rm /etc/nginx/sites-enabled/career-platform /etc/nginx/sites-available/career-platform
    sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    sudo systemctl reload nginx
    ```
  - **Result:** Before: `sites-enabled/` held only `default`. After: only `career-platform`. `nginx -t` printed `syntax is ok` and `test is successful`, and the reload succeeded. The first round of checks printed `200`, then **nothing** for the name, then `0`. The page title, fetched seconds later, was `Chris Owen Setioko | Information Systems & Business Analytics Student, …`, the same as port 8000 directly. Repeated 10 times: `200`, name present, 0 × `Welcome to nginx`, 0 × `Your Name`, the same 12,958 bytes every time. The app logged the missed request as `200`. The one empty result happened about 6 seconds after the reload and could not be reproduced. Its cause wasn't found.

- [x] **Step 3: Make Nginx restart itself too, and confirm it starts at boot**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo mkdir -p /etc/systemd/system/nginx.service.d
    sudo tee /etc/systemd/system/nginx.service.d/restart.conf > /dev/null <<'EOF'
    [Service]
    Restart=on-failure
    RestartSec=3
    EOF
    sudo systemctl daemon-reload
    ```
  - **Why:** Ubuntu's Nginx service doesn't restart after a crash by default. This *drop-in* file adds that one setting without editing the packaged file.
  - **Check:**
    ```bash
    systemctl show nginx -p Restart                    # Restart=on-failure
    systemctl is-enabled nginx                         # enabled
    systemctl is-active nginx                          # active
    sudo ss -ltnp | grep -E ':80 |:8000 '              # nginx on 0.0.0.0:80 and [::]:80; uvicorn on 127.0.0.1:8000 only
    ```
  - **Undo:** `sudo rm -r /etc/systemd/system/nginx.service.d && sudo systemctl daemon-reload`
  - **Result:** Before: `Restart=no`. After: `Restart=on-failure`, `RestartUSec=3s`. `nginx` and `career-platform` both `enabled` and `active`. `ss`: `nginx` on `0.0.0.0:80` and `[::]:80` (master pid 1784 as `root`, workers 1919 and 1920 as `www-data`); `uvicorn` and its workers on `127.0.0.1:8000` only.

### Task 4: Port 80 in the Azure firewall (about 2 min, Chris)

**Why this section:** The NSG is Azure's firewall in front of the VM. Even with Nginx listening, visitors can't reach port 80 unless a rule allows it.

- [x] **Step 1: Set `Allow-HTTP-80` to priority 320 on the right NSG**
  - **Where:** PORTAL → Network security groups → **`vm-career-platformNSG`** (not `vm-career-platform-nsg`) → Inbound security rules
  - **Run:** A rule named `Allow-HTTP-80` **already exists** here at priority 310 (TCP 80, from Any, Allow). Names must be unique within an NSG, so open it and change **Priority** to `320`, then Save. Leave everything else as is.
  - **Why:** It lets visitors in on port 80 only. There is still no rule for 8000.
  - **Check (LAPTOP):**
    ```bash
    az network nsg rule list -g rg-career-platform --nsg-name vm-career-platformNSG \
      --query "[].{name:name, port:destinationPortRange, prio:priority, src:sourceAddressPrefix}" -o table
    ```
    Exactly two rows: `Allow-HTTP-80  80  320  *` and `AllowSSHFromLaptop  22  1000  <your IP>/32`. Nothing for 8000.
  - **Undo:** Set the priority back to 310.
  - **Result:** Chris made the change in the portal before Task 3. The `az` check showed exactly two rows: `AllowSSHFromLaptop 22 1000 <laptop IP>/32` and `Allow-HTTP-80 80 320 *`. Nothing for 8000.

### Task 5: Verify from the outside (about 3 min)

**Why this section:** The real test is what a stranger on the internet sees. Your laptop is outside Azure, so it sees the same thing.

- [x] **Step 1: The site answers on port 80, and port 8000 doesn't**
  - **Where:** LAPTOP (a new tab, not the SSH session)
  - **Run:**
    ```bash
    curl -s -o /dev/null -w "%{http_code}\n" http://20.88.61.1/
    curl -s -o /dev/null -w "%{http_code}\n" http://20.88.61.1/static/css/styles.css
    curl -s http://20.88.61.1/ | grep -o "Chris Owen Setioko" | head -1
    curl -s http://20.88.61.1/ | grep -c "Your Name"
    curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://20.88.61.1:8000/
    ```
    Then open **http://20.88.61.1** in your browser.
  - **Check:** `200`, `200`, `Chris Owen Setioko`, `0`, then `000` after about 5 seconds (blocked, so no answer). The browser shows your styled resume with no `:8000` in the address bar.
  - **Undo:** Nothing to undo (read-only).
  - **Result (from the laptop):** `200`, `200`, `Chris Owen Setioko`, `0`. Port 8000 printed `000` after 5.02 seconds (curl exit 28, timed out), so it's blocked. The response header shows `Server: nginx/1.24.0 (Ubuntu)`, so visitors are served by Nginx. The browser check is Chris's to do.

| Requirement | Proved by |
| --- | --- |
| `http://PUBLIC-IP`, no port | Task 5: `200` + your name at `http://20.88.61.1/` |
| Starts at boot | `is-enabled` = `enabled` for `career-platform` (Task 2) and `nginx` (Task 3). Final proof: your reboot test |
| Comes back after a crash | `Restart=always` (app) and `Restart=on-failure` (Nginx). Final proof: your crash tests |
| One crash doesn't take the site down | Two workers under one supervisor (Task 2 `ps`). Final proof: your crash tests |
| Port 8000 closed to the internet | `127.0.0.1:8000` only (Task 3 `ss`), no NSG rule (Task 4), `000` from the laptop (Task 5) |
| App not running as root | Every `ps` line is `azureuser` (Task 2) |

---

## Record

A snapshot taken on 2026-10-07 at about 10:30 UTC, after Task 2 and before Task 3. The VM had rebooted at 10:24 UTC, and `career-platform` was active again by 10:24:10 without anyone starting it. Your laptop's IP address and the Azure subscription ID are deliberately left out, because this repo is public.

### Listening TCP ports (`sudo ss -ltnp` on the VM)

| Address : port | Program | What it is | Reachable from the internet? |
| --- | --- | --- | --- |
| `0.0.0.0:22` and `[::]:22` | `sshd` (socket held by `systemd`, pid 1) | SSH, how you log in. Ubuntu 24.04 lets systemd open the socket and hand connections to `sshd`. | Yes, but the NSG allows only your laptop |
| `127.0.0.1:8000` | `uvicorn` (supervisor) + 2 `python` workers | The app, the `career-platform` service | No: bound to localhost, and the NSG has no rule for 8000 |
| `127.0.0.53%lo:53` | `systemd-resolve` | The VM's own DNS cache (looks up names like `github.com`) | No: localhost only |
| `127.0.0.54:53` | `systemd-resolve` | A second local DNS address, same program | No: localhost only |

At the time of this snapshot, nothing listened on port 80. **After Task 3** (10:31 UTC), `ss` also shows `nginx` on `0.0.0.0:80` and `[::]:80`: the master process runs as `root` (it needs root to open port 80), and the workers that handle requests run as `www-data`. Reachable from the internet through `Allow-HTTP-80`.

### IP addresses

| | Address | Notes |
| --- | --- | --- |
| Private | `10.0.0.4` | On `eth0`, inside the Azure virtual network. Can't be reached from the internet. |
| Public | `20.88.61.1` | `vm-career-platformPublicIP`, Static, so it survives stop/start. Azure forwards it to `10.0.0.4`. |

### Inbound rules on `vm-career-platformNSG`

| Name | Priority | Port | From | Why it exists |
| --- | --- | --- | --- | --- |
| `Allow-HTTP-80` | 320 | TCP 80 | Anywhere | So visitors can load the site at `http://20.88.61.1` (Task 4 of this plan). |
| `AllowSSHFromLaptop` | 1000 | TCP 22 | Your laptop's public IP only (`/32`, left out here) | So you can SSH in for administration. No one else can even attempt to log in. |
| *(Azure defaults)* `AllowVnetInBound` | 65000 | Any | The virtual network | Lets machines in the same private network talk to each other. There are none besides this VM. |
| *(Azure defaults)* `AllowAzureLoadBalancerInBound` | 65001 | Any | Azure's load balancer | Azure's own health probes. |
| *(Azure defaults)* `DenyAllInBound` | 65500 | Any | Anywhere | Blocks everything the rules above don't allow, including port 8000. |

The leftover `vm-career-platform-nsg` has no custom rules and isn't attached to the VM's network card, so it has no effect.

---

## Day-to-day commands (VM)

```bash
sudo systemctl status career-platform      # is it running?
journalctl -u career-platform -f           # live app logs (Ctrl+C to stop watching)
sudo systemctl restart career-platform     # after a git pull or a .env change
sudo tail -f /var/log/nginx/access.log     # who's visiting
```

## Out of scope

- HTTPS (a domain name, a certificate, port 443), then `SESSION_COOKIE_SECURE=true` and enabling admin.
- Backups of `data/resume.db` and `data/public-profile.json`.
- Deleting the leftover NIC, NSG and public IP listed at the top. The unused public IP is still billed.
