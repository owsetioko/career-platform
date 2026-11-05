# AWS EC2 + RDS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve `csetioko.me` from one AWS EC2 server and a Single-AZ RDS PostgreSQL database instead of Railway, with the same data, working HTTPS, and Railway kept as the rollback.

**Architecture:** Visitors reach Nginx on an EC2 `t3.micro` (Ubuntu 24.04) through a reserved public IP. Nginx ends HTTPS with a Certbot certificate and forwards to Uvicorn on `127.0.0.1:8000`, run by systemd as an unprivileged user. Uvicorn talks over verified TLS to a private `db.t3.micro` RDS instance that accepts connections only from the server's firewall group. DNS stays in Cloudflare, "DNS only".

**Tech Stack:** AWS CLI 2, EC2, RDS for PostgreSQL 18.6, Ubuntu 24.04 (x86), Nginx, Certbot, systemd, uv, Python 3.12, FastAPI, Uvicorn, SQLAlchemy, psycopg 3.

**Status:** In progress, paused 2026-11-04. Tasks 2 and 3 are done: the firewall groups, SSH key, Elastic IP, EC2 server and RDS instance exist, and their IDs are in `~/.config/career-platform/aws.env`. The server is empty and DNS is unchanged, so Railway still serves the site. Tasks 0 and 1 are still open, and Task 1 comes next because the server clones this branch from GitHub. Their checkboxes below were not ticked as they ran.

**Differences from the steps below, as run:**
- RDS backup retention is 1 day, not 7. The account is on the free plan, which refused 7 (`FreeTierRestrictionError`).
- The SSH key has no passphrase, so server steps can run non-interactively. Add one afterwards with `ssh-keygen -p -f ~/.ssh/isba4775_aws`.
- Task 3's RDS step ran before the rest of Task 2, because only the firewall groups were needed for it.

**Spec:** Chris's request of 2026-11-04 ("EC2 for the app and a Single-AZ RDS PostgreSQL database; new branch so Railway doesn't redeploy from main; don't create anything yet"), plus his earlier choices: AWS CLI commands, Certbot on Nginx.

## How to read each step

- **Where:** `LAPTOP` (macOS Terminal in `~/Desktop/career-platform`), `SERVER` (SSH session as `ubuntu`), `CONSOLE` (AWS Console as root), or `CLOUDFLARE` (Cloudflare dashboard).
- Each step gives the commands, a **Check** with the expected result, and an **Undo** where one isn't obvious.

Run the steps in order. If a **Check** doesn't match, stop there.

## Global Constraints

- AWS: profile `isba-4775`, region `us-east-1`. Every `LAPTOP` terminal starts with the **Session setup** below.
- Branch: all repo work stays on `aws-ec2-rds-migration`. **Nothing reaches `main` until Task 8**, because a push to `main` redeploys Railway.
- This repo is **public**. Never commit passwords, `.env`, dumps, the server's IP, or the AWS account ID. Resource IDs and passwords live in `~/.config/career-platform/aws.env` (mode 600), outside the repo.
- Stay inside the `ISBA4775EC2Migration` policy. If a command is denied, stop and tell Chris. Don't try to widen it or work around it.
- Sizes: EC2 `t3.micro`, RDS `db.t3.micro`, Single-AZ, PostgreSQL `18.6`, availability zone `us-east-1a` for both.
- RDS is never publicly accessible. Port 5432 accepts only the server's security group. Port 8000 is never opened.
- The app never runs as root. Don't set `FORWARDED_ALLOW_IPS`: the default `127.0.0.1` is correct behind local Nginx, and Railway's `*` would let visitors fake their IP.
- `python -m app.database` must not run against RDS until the data is restored (Task 5). On an empty database it creates the placeholder profile.
- A `200` proves nothing here. "Working" means the page contains `Chris Owen Setioko` and contains neither `temporarily unavailable` nor `Your Name`.
- In zsh, always write `${VAR}`, never `$VAR` next to a `:`. zsh reads `$A:u` as a modifier and corrupts the value.

**Session setup** (`LAPTOP`, every new terminal):

```bash
export AWS_PROFILE=isba-4775 AWS_REGION=us-east-1
mkdir -p -m 700 ~/.config/career-platform
touch ~/.config/career-platform/aws.env && chmod 600 ~/.config/career-platform/aws.env
source ~/.config/career-platform/aws.env
```

## Checked against the account (2026-11-04)

| Item | Result |
| --- | --- |
| EC2 launch command in Task 3, dry run | Allowed |
| `t4g.*`, `t3a.micro`, `t2.micro` | Denied by the policy, which is why this plan uses x86 |
| Security groups, Elastic IP, tags, `import-key-pair` | Allowed (dry run). `create-key-pair` is denied, so the key is made on the laptop |
| `db.t3.micro` + gp3 on 18.6 in `us-east-1a` | Offered |
| **`rds:CreateDBInstance`** | **Untested.** RDS has no dry run, so Task 3 is the first real test |
| Session Manager, S3, IAM, budgets, account plan, CloudWatch Logs | Denied to `isba-student`. Hence SSH, backups kept on the laptop, and Task 0 run as root |

## Decisions

1. **SSH, not Session Manager.** Session Manager needs SSM and an IAM role, and the policy denies both. Port 22 is limited to the laptop's current IP.
2. **Certbot's HTTP check.** It's what Chris used on Azure, but it can't succeed until DNS points at the server, so HTTPS is down for a few minutes at cutover. Certbot's Cloudflare DNS check would avoid that, at the cost of storing a Cloudflare API token on the server. For a low-traffic resume site, the short gap is the better trade.
3. **`db.t3.micro`, not `db.t4g.micro`.** The EC2 side of the policy denies `t4g`, so the same is assumed for RDS. If `db.t3.micro` is denied, stop rather than trying other sizes.
4. **A dedicated `career` system user in `/opt/career-platform`.** The default `ubuntu` user can become root without a password, so an app running as `ubuntu` is one bug away from root. This also follows the README's guidance.
5. **A separate `career_app` database role that owns only its own database.** The RDS master account stays out of the app's configuration.
6. **Admin stays off**, as in production today: no `ADMIN_PASSWORD_HASH` or `SESSION_SECRET` on the server. This also freezes the data during the move. `app/admin.py` has no login rate limiting, so add that before ever turning admin on.
7. **Logs are kept 30 days**, and the privacy page says so. AWS doesn't hold them; they live on the server.
8. **Railway stays up for 14 days** after cutover as the rollback (Task 9).

## Cost estimate

Rough us-east-1 on-demand prices, from memory. Confirm in the AWS Pricing Calculator.

| Item | Per month |
| --- | --- |
| EC2 `t3.micro` | ≈ $7.60 |
| Public IPv4 (Elastic IP) | ≈ $3.65 |
| EC2 disk, 16 GB gp3 | ≈ $1.30 |
| RDS `db.t3.micro` | ≈ $13.15 |
| RDS storage, 20 GB gp3 | ≈ $2.30 |
| **Total** | **≈ $28** |

This replaces the earlier $24–25 estimate, which assumed ARM servers. Stopping the server doesn't stop the IP, disk or database charges. Only the teardown does.

## Review Focus

The most likely ways this looks done but isn't:

1. **The page renders from a fallback.** A missing `DATABASE_URL` silently selects SQLite, and a failed read serves the snapshot or starter profile with a `200`. Tasks 6 and 7 check the content, and Task 6 proves the app's own connection uses TLS to RDS.
2. **The placeholder profile lands in RDS.** This happens if `python -m app.database` or the service runs before the restore. Task 5 restores first and compares every table's checksum with Railway, and Task 6 compares again after the app has started.
3. **Email breaks during the DNS change.** MX, SPF, DKIM and DMARC share the Cloudflare zone with the web records. Task 7 edits only `csetioko.me` and `www`, and checks those mail records before and after.
4. **The certificate works today and fails to renew.** Port 80 must stay open and the Certbot timer must be active. Task 7 runs `certbot renew --dry-run` after the real certificate exists.
5. **SSH stops working when the laptop's IP changes.** Campus Wi-Fi and hotspots change it. The server looks down when it isn't. See "Day-to-day commands".

---

### Task 0: Account checks as root (about 10 min, Chris)

`isba-student` is denied these, so they happen in the Console.

- [ ] **Step 1: Find out which plan the account is on**
  - **Where:** CONSOLE → Billing → Free Tier / Credits.
  - **Check:** note the plan, the credit balance and the credit expiry date. On the free plan, the account closes at the end of the period or when credits run out, and its contents are deleted after a further 90 days, so upgrade before relying on it. At about $28/month, $100 of credit lasts about 3.5 months.

- [ ] **Step 2: Create a budget alert**
  - **Where:** CONSOLE → Billing → Budgets → Create budget → Monthly cost budget, $35, alert to your email.
  - **Check:** the budget is listed. It warns only; it doesn't stop spending.

- [ ] **Step 3: Confirm root has MFA**
  - **Where:** CONSOLE → IAM dashboard.
  - **Check:** no MFA warning for root.

### Task 1: Prepare the repo (about 30 min)

**Files:**
- Modify: `app/templates/privacy.html` (the lines naming Railway, plus the "Last updated" date), `.env.example`
- Test: `tests/test_app.py`
- Create: `deploy/career-platform.service`, `deploy/nginx-career-platform.conf`, `deploy/deploy.sh`, `deploy/db-fingerprint.sql`

**Produces:** the four `deploy/` files that Tasks 5 to 8 use.

- [ ] **Step 1: Write the failing test** in `tests/test_app.py`, next to `test_privacy_page_renders_without_database` and using its setup:

  ```python
  def test_privacy_page_names_aws_as_host(monkeypatch) -> None:
      _install_unavailable_database(monkeypatch)

      response = TestClient(app).get("/privacy")

      assert "Amazon Web Services" in response.text
      assert "up to 30 days" in response.text
      assert "Railway" not in response.text
  ```

- [ ] **Step 2: Run it to verify it fails**
  - **Run:** `.venv/bin/python -m pytest tests/test_app.py::test_privacy_page_names_aws_as_host -v`
  - **Check:** FAIL on the `Amazon Web Services` assertion.

- [ ] **Step 3: Update `app/templates/privacy.html`** with exactly this copy, and set "Last updated" to the day of the edit:
  - Hosting logs paragraph: `The site runs on a server I manage at Amazon Web Services (AWS). For each request, the server's logs record your IP address, the time, the page you asked for, whether it loaded, the page that linked you here and your browser's identifying string.`
  - Who sees it: `<strong>Amazon Web Services</strong> hosts the server and database. The logs stay on that server.`
  - How long: `<strong>Hosting logs:</strong> up to 30 days, then deleted automatically.`

- [ ] **Step 4: Run the full test suite**
  - **Run:** `.venv/bin/python -m pytest -q`
  - **Check:** all pass (77 passed and 3 skipped before this task, so 78 passed now).

- [ ] **Step 5: Create `deploy/career-platform.service`**

  ```ini
  [Unit]
  Description=Career platform (Uvicorn)
  After=network-online.target
  Wants=network-online.target

  [Service]
  User=career
  Group=career
  WorkingDirectory=/opt/career-platform
  ExecStart=/opt/career-platform/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
  Restart=always
  RestartSec=3
  UMask=0077

  [Install]
  WantedBy=multi-user.target
  ```

- [ ] **Step 6: Create `deploy/nginx-career-platform.conf`**

  ```nginx
  server {
      listen 80 default_server;
      listen [::]:80 default_server;
      server_name csetioko.me;

      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }

  server {
      listen 80;
      listen [::]:80;
      server_name www.csetioko.me;
      return 301 https://csetioko.me$request_uri;
  }
  ```

- [ ] **Step 7: Create `deploy/deploy.sh`** (run on the server as `ubuntu`). It must use `set -euo pipefail` and, in order:
  1. Run as `career`, in `/opt/career-platform`: `git pull --ff-only`, `uv sync --locked --no-dev`, `.venv/bin/python -m app.database`.
  2. Run `sudo systemctl restart career-platform`, then wait 3 seconds.
  3. Fetch `http://127.0.0.1:8000/` once into a variable, and exit non-zero with a clear message unless it contains `Chris Owen Setioko` and contains neither `temporarily unavailable` nor `Your Name`.

- [ ] **Step 8: Create `deploy/db-fingerprint.sql`.** It prints each table's exact row count and content checksum, plus each sequence's position. Sorting uses `collate "C"` because text order otherwise varies between servers, which caused a false mismatch in the 2026-11-02 restore test.

  ```sql
  select 'table' as kind, c.relname as name,
         (xpath('/row/n/text()', query_to_xml(format('select count(*) as n from public.%I', c.relname), false, true, '')))[1]::text as value,
         (xpath('/row/h/text()', query_to_xml(format('select md5(coalesce(string_agg(t::text, ''|'' order by t::text collate "C"), '''')) as h from public.%I t', c.relname), false, true, '')))[1]::text as checksum
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind = 'r'
  union all
  select 'sequence', sequencename, coalesce(last_value::text, 'unused'), ''
  from pg_sequences where schemaname = 'public'
  order by 1, 2;
  ```

- [ ] **Step 9: Update the `FORWARDED_ALLOW_IPS` comment in `.env.example`** to: `Proxies trusted for X-Forwarded-Proto/-For. Default 127.0.0.1 is right behind local Nginx; use * only on a platform like Railway.`

- [ ] **Step 10: Commit and push the branch**
  - **Before pushing:** in Railway, confirm the web service deploys only from `main` (Settings → Source) and that PR environments are off. The server clones this branch in Task 4, so it must be on GitHub.
  - **Run:**
    ```bash
    bash -n deploy/deploy.sh
    git add .gitignore app/templates/privacy.html tests/test_app.py .env.example deploy docs/superpowers/plans/2026-11-04-aws-ec2-rds-migration.md
    git status --short
    git commit -m "feat: prepare EC2 and RDS deployment files"
    git push -u origin aws-ec2-rds-migration
    ```
  - **Check:** `git status --short` lists only those paths as staged, with nothing from `.env`, `data/` or `backups/`. Railway shows no new deployment.

### Task 2: Create the network pieces (about 10 min)

**Produces:** in `aws.env`: `WEB_SG`, `DB_SG`, `EIP`, `EIP_ALLOC`, `SUBNET`. SSH key `~/.ssh/isba4775_aws`.

- [ ] **Step 1: Make the SSH key and import it**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    ssh-keygen -t ed25519 -f ~/.ssh/isba4775_aws -C isba4775-aws
    aws ec2 import-key-pair --key-name isba4775-aws --public-key-material fileb://$HOME/.ssh/isba4775_aws.pub
    ```
  - **Check:** the output shows `KeyName: isba4775-aws`. Set a passphrase when prompted.
  - **Undo:** `aws ec2 delete-key-pair --key-name isba4775-aws`

- [ ] **Step 2: Create the two firewall groups**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
    SUBNET=$(aws ec2 describe-subnets --filters Name=vpc-id,Values=${VPC} Name=availability-zone,Values=us-east-1a --query 'Subnets[0].SubnetId' --output text)
    WEB_SG=$(aws ec2 create-security-group --group-name career-platform-web --description "Career platform web server" --vpc-id ${VPC} --query GroupId --output text)
    DB_SG=$(aws ec2 create-security-group --group-name career-platform-db --description "Career platform database" --vpc-id ${VPC} --query GroupId --output text)
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    aws ec2 authorize-security-group-ingress --group-id ${WEB_SG} --protocol tcp --port 22 --cidr ${MY_IP}/32
    aws ec2 authorize-security-group-ingress --group-id ${WEB_SG} --protocol tcp --port 80 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id ${WEB_SG} --protocol tcp --port 443 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id ${DB_SG} --protocol tcp --port 5432 --source-group ${WEB_SG}
    aws ec2 create-tags --resources ${WEB_SG} ${DB_SG} --tags Key=Project,Value=career-platform
    printf 'SUBNET=%s\nWEB_SG=%s\nDB_SG=%s\n' "${SUBNET}" "${WEB_SG}" "${DB_SG}" >> ~/.config/career-platform/aws.env
    ```
  - **Check:**
    ```bash
    aws ec2 describe-security-groups --group-ids ${WEB_SG} ${DB_SG} --query 'SecurityGroups[].[GroupName,IpPermissions[].[FromPort,IpRanges[].CidrIp,UserIdGroupPairs[].GroupId]]' --output json
    ```
    The web group has 22 (your `/32` only), 80 and 443 (anywhere). The database group has only 5432, from the web group. No `0.0.0.0/0` on 22 or 5432.
  - **Undo:** `aws ec2 delete-security-group --group-id ${DB_SG}`, then the same for `${WEB_SG}`.

- [ ] **Step 3: Reserve the public IP**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    read -r EIP EIP_ALLOC <<< "$(aws ec2 allocate-address --domain vpc --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Project,Value=career-platform}]' --query '[PublicIp,AllocationId]' --output text)"
    printf 'EIP=%s\nEIP_ALLOC=%s\n' "${EIP}" "${EIP_ALLOC}" >> ~/.config/career-platform/aws.env
    echo "${EIP}"
    ```
  - **Check:** prints one IP address. It bills from now on, so carry on or undo.
  - **Undo:** `aws ec2 release-address --allocation-id ${EIP_ALLOC}`

### Task 3: Create the database and server (about 20 min, mostly waiting)

**Consumes:** `SUBNET`, `WEB_SG`, `DB_SG`, `EIP_ALLOC`.
**Produces:** in `aws.env`: `INSTANCE_ID`, `RDS_HOST`, `MASTER_PW`, `APP_PW`.

- [ ] **Step 1: Create the RDS instance.** This is the first test of `rds:CreateDBInstance`.
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    MASTER_PW=$(openssl rand -hex 24); APP_PW=$(openssl rand -hex 24)
    printf 'MASTER_PW=%s\nAPP_PW=%s\n' "${MASTER_PW}" "${APP_PW}" >> ~/.config/career-platform/aws.env
    aws rds create-db-instance \
      --db-instance-identifier career-platform-db \
      --engine postgres --engine-version 18.6 \
      --db-instance-class db.t3.micro \
      --allocated-storage 20 --storage-type gp3 --storage-encrypted \
      --no-multi-az --availability-zone us-east-1a \
      --no-publicly-accessible \
      --vpc-security-group-ids ${DB_SG} \
      --master-username career_admin --master-user-password "${MASTER_PW}" \
      --backup-retention-period 7 --copy-tags-to-snapshot \
      --deletion-protection \
      --tags Key=Project,Value=career-platform \
      --query 'DBInstance.DBInstanceStatus' --output text
    ```
  - **Why:** hex passwords have no characters that need escaping in a URL.
  - **Check:** prints `creating`. If it's denied, stop and tell Chris. If it fails only on backup retention (a free-plan limit), rerun with `--backup-retention-period 1` and note it.
  - **Undo:** see "Teardown".

- [ ] **Step 2: Launch the server**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
    INSTANCE_ID=$(aws ec2 run-instances --image-id ${AMI} --instance-type t3.micro \
      --key-name isba4775-aws --subnet-id ${SUBNET} --security-group-ids ${WEB_SG} \
      --metadata-options HttpTokens=required,HttpEndpoint=enabled \
      --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=16,VolumeType=gp3,Encrypted=true,DeleteOnTermination=true}' \
      --tag-specifications 'ResourceType=instance,Tags=[{Key=Project,Value=career-platform},{Key=Name,Value=career-platform-web}]' \
      --query 'Instances[0].InstanceId' --output text)
    printf 'INSTANCE_ID=%s\n' "${INSTANCE_ID}" >> ~/.config/career-platform/aws.env
    aws ec2 wait instance-status-ok --instance-ids ${INSTANCE_ID}
    aws ec2 associate-address --instance-id ${INSTANCE_ID} --allocation-id ${EIP_ALLOC}
    ```
  - **Check:** `ssh -i ~/.ssh/isba4775_aws ubuntu@${EIP} 'lsb_release -ds; uname -m'` prints `Ubuntu 24.04...` and `x86_64`.

- [ ] **Step 3: Wait for RDS and save its address**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    aws rds wait db-instance-available --db-instance-identifier career-platform-db
    RDS_HOST=$(aws rds describe-db-instances --db-instance-identifier career-platform-db --query 'DBInstances[0].Endpoint.Address' --output text)
    printf 'RDS_HOST=%s\n' "${RDS_HOST}" >> ~/.config/career-platform/aws.env
    aws rds describe-db-instances --db-instance-identifier career-platform-db --query 'DBInstances[0].[EngineVersion,DBInstanceClass,MultiAZ,PubliclyAccessible,StorageEncrypted,DeletionProtection,BackupRetentionPeriod]' --output text
    ```
  - **Check:** prints `18.6  db.t3.micro  False  False  True  True  7` (retention `1` if Step 1 needed it).

### Task 4: Set up the server (about 15 min)

**Produces:** the `career` user, code in `/opt/career-platform`, packages, the RDS certificate bundle.

- [ ] **Step 1: Install packages**
  - **Where:** SERVER (`ssh -i ~/.ssh/isba4775_aws ubuntu@${EIP}`)
  - **Run:**
    ```bash
    sudo apt-get update && sudo apt-get -y upgrade
    sudo apt-get install -y nginx certbot python3-certbot-nginx git postgresql-common
    sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
    sudo apt-get install -y postgresql-client-18
    curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh
    ```
  - **Why:** Ubuntu's own packages are older than Postgres 18, so the client tools come from the PostgreSQL project's repository.
  - **Check:** `pg_restore --version` shows 18.x. `uv --version` and `certbot --version` print versions. `systemctl is-active nginx` prints `active`.

- [ ] **Step 2: Add swap, log retention and automatic security updates**
  - **Where:** SERVER
  - **Run:**
    ```bash
    sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    sudo mkdir -p /etc/systemd/journald.conf.d
    printf '[Journal]\nMaxRetentionSec=30day\n' | sudo tee /etc/systemd/journald.conf.d/retention.conf
    sudo systemctl restart systemd-journald
    printf 'Unattended-Upgrade::Automatic-Reboot "true";\nUnattended-Upgrade::Automatic-Reboot-Time "10:00";\n' | sudo tee /etc/apt/apt.conf.d/52career-reboot
    ```
  - **Why:** 1 GB of RAM leaves little margin during updates. Thirty days matches the privacy page; Nginx's logs already rotate out after 14. Reboots at 10:00 UTC fall in the small hours Pacific.
  - **Check:** `swapon --show` lists `/swapfile`. `systemctl is-enabled unattended-upgrades` prints `enabled`.

- [ ] **Step 3: Create the app user and get the code**
  - **Where:** SERVER
  - **Run:**
    ```bash
    sudo useradd --system --create-home --home-dir /var/lib/career --shell /usr/sbin/nologin career
    sudo install -d -o career -g career /opt/career-platform
    sudo -u career git clone --branch aws-ec2-rds-migration https://github.com/owsetioko/career-platform.git /opt/career-platform
    sudo -u career sh -c 'cd /opt/career-platform && uv sync --locked --no-dev'
    sudo install -d -m 755 /etc/career-platform
    sudo curl -fsSo /etc/career-platform/rds-global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
    sudo chmod 644 /etc/career-platform/rds-global-bundle.pem
    ```
  - **Check:** `sudo -u career /opt/career-platform/.venv/bin/python -c "import psycopg, argon2, fastapi; print('ok')"` prints `ok`. `sudo -u career git -C /opt/career-platform branch --show-current` prints `aws-ec2-rds-migration`.

### Task 5: Create the app database and restore your data (about 15 min)

**Consumes:** `RDS_HOST`, `MASTER_PW`, `APP_PW`, `deploy/db-fingerprint.sql`.
**Produces:** RDS database `career_platform`, owned by role `career_app`, holding your data. `/opt/career-platform/.env`.

- [ ] **Step 1: Create the role and database**
  - **Where:** LAPTOP (sends the commands over SSH, so the passwords stay out of your shell history)
  - **Run:**
    ```bash
    CA='sslmode=verify-full&sslrootcert=/etc/career-platform/rds-global-bundle.pem'
    ssh -i ~/.ssh/isba4775_aws ubuntu@${EIP} "psql 'postgresql://career_admin:${MASTER_PW}@${RDS_HOST}:5432/postgres?${CA}' -v ON_ERROR_STOP=1 -c \"CREATE ROLE career_app LOGIN PASSWORD '${APP_PW}'\" -c 'GRANT career_app TO career_admin' -c 'CREATE DATABASE career_platform OWNER career_app' -Atc \"select datcollate, pg_get_userbyid(datdba) from pg_database where datname='career_platform'\""
    ```
  - **Why:** owning the database lets `career_app` create tables, with no rights over anything else. The `GRANT` is required by PostgreSQL 16+ before an admin can create a database owned by another role. This is also the first proof that the server can reach RDS with a verified certificate.
  - **Check:** the last line is `en_US.UTF-8|career_app`, matching Railway's sort order. If the locale differs, stop and tell Chris.

- [ ] **Step 2: Write the server's `.env`**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    printf 'APP_TITLE=Personal Resume Platform\nDATABASE_URL=postgresql://career_app:%s@%s:5432/career_platform?sslmode=verify-full&sslrootcert=/etc/career-platform/rds-global-bundle.pem\nGA_MEASUREMENT_ID=G-X0HGGMK1T8\n' "${APP_PW}" "${RDS_HOST}" \
      | ssh -i ~/.ssh/isba4775_aws ubuntu@${EIP} 'sudo -u career sh -c "umask 077; cat > /opt/career-platform/.env"'
    ```
  - **Check:** on the SERVER, `sudo ls -l /opt/career-platform/.env` shows `-rw-------` owned by `career`.

- [ ] **Step 3: Take a fresh Railway backup and record its fingerprint**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    set -a; source .env; set +a
    PG18=/opt/homebrew/opt/postgresql@18/bin
    DUMP=backups/railway-$(date +%Y-%m-%d-%H%M).dump
    ${PG18}/pg_dump "${RAILWAY_DATABASE_URL}" --format=custom --no-owner --no-acl --file="${DUMP}"
    chmod 600 "${DUMP}"; shasum -a 256 "${DUMP}" > "${DUMP}.sha256"
    ${PG18}/psql "${RAILWAY_DATABASE_URL}" -At -F' | ' -f deploy/db-fingerprint.sql > backups/railway.fp
    scp -i ~/.ssh/isba4775_aws "${DUMP}" ubuntu@${EIP}:/tmp/railway.dump
    ```
  - **Check:** `backups/railway.fp` lists 8 tables and 6 sequences. `pg_dump` needs the Postgres 18 path; the default on your PATH is 17 and refuses to run. If Railway refuses the connection, get the current `DATABASE_PUBLIC_URL` again.

- [ ] **Step 4: Restore into RDS**
  - **Where:** SERVER
  - **Run:**
    ```bash
    DB=$(sudo grep '^DATABASE_URL=' /opt/career-platform/.env | cut -d= -f2-)
    pg_restore -d "${DB}" --no-owner --no-acl --single-transaction --exit-on-error /tmp/railway.dump
    psql "${DB}" -At -F' | ' -f /opt/career-platform/deploy/db-fingerprint.sql > /tmp/rds.fp
    rm /tmp/railway.dump
    ```
  - **Check:** no errors. The dump is removed from the server. A failure rolls back fully, because the restore is a single transaction.

- [ ] **Step 5: Compare RDS with Railway**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    scp -i ~/.ssh/isba4775_aws ubuntu@${EIP}:/tmp/rds.fp backups/rds.fp
    diff backups/railway.fp backups/rds.fp && echo IDENTICAL
    ```
  - **Check:** prints `IDENTICAL`. Any difference means stop.

### Task 6: Run the app behind Nginx and test it before DNS moves (about 15 min)

**Consumes:** `deploy/career-platform.service`, `deploy/nginx-career-platform.conf`, `deploy/deploy.sh`.

- [ ] **Step 1: Install and start the service**
  - **Where:** SERVER
  - **Run:**
    ```bash
    sudo cp /opt/career-platform/deploy/career-platform.service /etc/systemd/system/
    systemd-analyze verify /etc/systemd/system/career-platform.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now career-platform
    ```
  - **Check:**
    ```bash
    systemctl is-active career-platform                                   # active
    sudo ss -ltnp 'sport = :8000'                                          # 127.0.0.1:8000 only
    curl -s http://127.0.0.1:8000/ | grep -c 'Chris Owen Setioko'          # 1 or more
    curl -s http://127.0.0.1:8000/ | grep -cE 'temporarily unavailable|Your Name'   # 0
    curl -s http://127.0.0.1:8000/ | grep -c 'G-X0HGGMK1T8'                # 1 (analytics banner still on)
    sudo journalctl -u career-platform -n 30 --no-pager | grep -c Traceback  # 0
    ```

- [ ] **Step 2: Prove the app uses RDS over TLS**
  - **Where:** SERVER
  - **Run:**
    ```bash
    sudo -u career sh -c 'cd /opt/career-platform && .venv/bin/python -c "
    from sqlalchemy import text
    from app.database import create_database_engine
    with create_database_engine().connect() as c:
        print(c.execute(text(\"select ssl from pg_stat_ssl where pid = pg_backend_pid()\")).scalar(), c.execute(text(\"select current_user, current_database()\")).one())
    "'
    ```
  - **Check:** prints `True ('career_app', 'career_platform')`.

- [ ] **Step 3: Install the Nginx site**
  - **Where:** SERVER
  - **Run:**
    ```bash
    sudo cp /opt/career-platform/deploy/nginx-career-platform.conf /etc/nginx/sites-available/career-platform
    sudo ln -s /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
    sudo rm /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    sudo mkdir -p /etc/systemd/system/nginx.service.d
    printf '[Service]\nRestart=on-failure\nRestartSec=3\n' | sudo tee /etc/systemd/system/nginx.service.d/restart.conf
    sudo systemctl daemon-reload
    ```
  - **Check:** `nginx -t` reports `test is successful`. `systemctl show nginx -p Restart` prints `Restart=on-failure`.

- [ ] **Step 4: Test the deploy script and data once more**
  - **Where:** SERVER, then LAPTOP
  - **Run:** on the SERVER, `bash /opt/career-platform/deploy/deploy.sh`, then rerun the Task 5 Step 4 `psql ... > /tmp/rds.fp` line. Then rerun Task 5 Step 5 on the LAPTOP.
  - **Check:** the script exits 0 and the fingerprint still prints `IDENTICAL`, proving `python -m app.database` changed nothing.

- [ ] **Step 5: Test from outside, before touching DNS**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    curl -s --resolve csetioko.me:80:${EIP} http://csetioko.me/ | grep -c 'Chris Owen Setioko'
    curl -s --resolve csetioko.me:80:${EIP} http://csetioko.me/ | grep -cE 'temporarily unavailable|Your Name|Welcome to nginx'
    curl -s --resolve csetioko.me:80:${EIP} http://csetioko.me/privacy | grep -c 'Amazon Web Services'
    curl -s -o /dev/null -w '%{http_code}\n' --resolve csetioko.me:80:${EIP} http://csetioko.me/static/css/styles.css
    nc -vz -w 5 ${EIP} 8000
    nc -vz -w 5 ${RDS_HOST} 5432
    ```
  - **Check:** at least 1, then `0`, then at least 1, then `200`. Both `nc` commands fail or time out; if either connects, stop and fix the firewall.

- [ ] **Step 6: Reboot test**
  - **Where:** SERVER: `sudo reboot`. Wait a minute, then rerun Step 5's first two commands from the LAPTOP.
  - **Check:** same results, with the same IP.

### Task 7: Cut over DNS and get HTTPS (about 15 min, Chris in Cloudflare)

Nothing visitors see changes until Step 3. Pick a quiet time. Expect HTTPS to be down for a few minutes between Steps 3 and 5.

- [ ] **Step 1: Record the mail records**
  - **Where:** LAPTOP
  - **Run:** `dig +short csetioko.me MX > backups/mail-before.txt; dig +short csetioko.me TXT >> backups/mail-before.txt; dig +short _dmarc.csetioko.me TXT >> backups/mail-before.txt; dig +short zmail._domainkey.csetioko.me TXT >> backups/mail-before.txt; cat backups/mail-before.txt`
  - **Check:** shows the Zoho MX records, SPF, DMARC and DKIM.

- [ ] **Step 2: Confirm the data hasn't changed since the restore**
  - **Where:** LAPTOP
  - **Run:** rerun the fingerprint line from Task 5 Step 3 (the `psql ... > backups/railway.fp` command, after `source .env`), then `diff backups/railway.fp backups/rds.fp && echo IDENTICAL`.
  - **Check:** prints `IDENTICAL`. If not, go back to Task 5: drop and recreate the database, then restore again.

- [ ] **Step 3: Change exactly two DNS records**
  - **Where:** CLOUDFLARE → `csetioko.me` → DNS → Records.
  - **Do:**
    - `csetioko.me`: replace the Railway CNAME with an **A record** → your Elastic IP, Proxy status **DNS only**, TTL Auto.
    - `www`: edit the A record (it still points at the old Azure VM, `20.88.61.1`) → your Elastic IP, **DNS only**.
    - Touch nothing else: not MX, TXT, `zmail._domainkey` or `_dmarc`.
  - **Check:** `dig +short csetioko.me @1.1.1.1` and `dig +short www.csetioko.me @1.1.1.1` both print your Elastic IP.
  - **Undo:** see "Rollback".

- [ ] **Step 4: Dry-run the certificate**
  - **Where:** SERVER
  - **Run:** `sudo certbot certonly --nginx --dry-run -d csetioko.me -d www.csetioko.me --agree-tos -m chris@csetioko.me --no-eff-email`
  - **Check:** `The dry run was successful`. This uses Let's Encrypt's test system, so failures here don't count against its rate limits. Fix any failure here before Step 5.

- [ ] **Step 5: Get the real certificate**
  - **Where:** SERVER
  - **Run:** `sudo certbot --nginx -d csetioko.me -d www.csetioko.me --redirect --agree-tos -m chris@csetioko.me --no-eff-email`
  - **Check:** `Successfully deployed certificate` for both names. `sudo nginx -t` is successful.

- [ ] **Step 6: Verify everything from outside**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    curl -s https://csetioko.me/ | grep -c 'Chris Owen Setioko'
    curl -s https://csetioko.me/ | grep -cE 'temporarily unavailable|Your Name'
    curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' http://csetioko.me/
    curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' https://www.csetioko.me/
    curl -sI https://csetioko.me/ | grep -iE '^server|railway'
    echo | openssl s_client -connect csetioko.me:443 -servername csetioko.me 2>/dev/null | openssl x509 -noout -issuer -enddate -ext subjectAltName
    dig +short csetioko.me MX > /tmp/m; dig +short csetioko.me TXT >> /tmp/m; dig +short _dmarc.csetioko.me TXT >> /tmp/m; dig +short zmail._domainkey.csetioko.me TXT >> /tmp/m; sort /tmp/m | diff - <(sort backups/mail-before.txt) && echo MAIL-UNCHANGED
    ```
  - **Check:** at least 1, then `0`. Both redirects are `301` to `https://csetioko.me/`. The `server` header says `nginx` and there's no `x-railway` header. The certificate is from Let's Encrypt and lists both names. `MAIL-UNCHANGED` prints.

- [ ] **Step 7: Check renewal, email and the browser**
  - **Where:** SERVER, then your browser and mailbox
  - **Run:** `sudo certbot renew --dry-run` and `systemctl list-timers | grep certbot`.
  - **Check:** the renewal dry run succeeds and the timer is listed. Send an email to `chris@csetioko.me` from Gmail and reply to it. Open the site in a private window: the padlock is fine, styling loads, and the analytics banner appears.

### Task 8: Finish the move in the repo (about 30 min, after 48 quiet hours)

Merging here is what redeploys Railway. Railway isn't serving anyone by now, but after this merge its copy of the privacy page says AWS, so a rollback would need a follow-up fix.

**Files:**
- Modify: `README.md` (deploy section, costs table), `docs/architecture.md` (new "Now: AWS" diagram, Railway moved to "Before"), `docs/how-this-site-is-secured.md` (AWS firewall wording, new certificate details)

- [ ] **Step 1: Close the temporary access**
  - **Where:** Railway dashboard, then LAPTOP.
  - **Do:** remove the Postgres service's public TCP proxy. Remove `RAILWAY_DATABASE_URL` from `.env`.
  - **Check:** `nc -vz -w 5` to the old proxy address no longer gets a Postgres answer. The Railway web app, if visited directly, still loads over its private connection.

- [ ] **Step 2: Update the three docs.** Replace the Railway deploy steps in `README.md` with: the server layout, `deploy/deploy.sh`, the SSH command, and the firewall update for a changed laptop IP. Don't include the Elastic IP or account ID. Add the AWS row to the costs table with real figures from Billing.

- [ ] **Step 3: Run the tests, merge and push**
  - **Where:** LAPTOP
  - **Run:**
    ```bash
    .venv/bin/python -m pytest -q
    git add README.md docs/architecture.md docs/how-this-site-is-secured.md
    git commit -m "docs: describe the AWS deployment"
    git switch main && git pull --ff-only
    git merge --no-ff aws-ec2-rds-migration
    git push origin main
    ```
  - **Check:** tests pass and the push succeeds.

- [ ] **Step 4: Put the server on `main`**
  - **Where:** SERVER
  - **Run:** `sudo -u career git -C /opt/career-platform fetch origin main && sudo -u career git -C /opt/career-platform switch main && bash /opt/career-platform/deploy/deploy.sh`
  - **Check:** the script exits 0 and `https://csetioko.me/` still passes Task 7 Step 6.

### Task 9: Retire Railway (about 10 min, Chris, 14 days after cutover)

- [ ] **Step 1: Take a final local copy of the RDS data.** On the SERVER: `pg_dump "${DB}" --format=custom --no-owner --no-acl --file=/tmp/rds-final.dump`, with `DB` set as in Task 5 Step 4. `scp` it to `backups/` on the LAPTOP, then delete it from the server.
  - **Check:** the file exists in `backups/`. This off-AWS copy matters because RDS backups disappear if the account closes.
- [ ] **Step 2: Delete the Railway project.** Railway dashboard → project → Settings → Danger. **This removes the rollback, and it can't be undone.**
  - **Check:** `https://csetioko.me/` still works. Remove `railway.json` in a follow-up commit.

---

## Rollback

Available until Task 9. No data changes during the move, because admin is off.

1. In CLOUDFLARE, change `csetioko.me` back to a **CNAME** → `tbtcq5cj.up.railway.app`, **DNS only**. Leave `www` as it is, or point it the same way if Railway has that domain configured.
2. **Check:** `curl -sI https://csetioko.me/ | grep -i x-railway` shows a header. If the Task 8 merge has happened, revert the privacy page on `main`.

AWS keeps running, and billing, until you run the teardown.

## Day-to-day commands

```bash
# LAPTOP: connect
source ~/.config/career-platform/aws.env; ssh -i ~/.ssh/isba4775_aws ubuntu@${EIP}

# LAPTOP: SSH times out because your IP changed. Add the new IP, and revoke the old /32
AWS_PROFILE=isba-4775 aws ec2 authorize-security-group-ingress --group-id ${WEB_SG} --protocol tcp --port 22 --cidr $(curl -s https://checkip.amazonaws.com)/32

# SERVER: deploy the latest code
bash /opt/career-platform/deploy/deploy.sh

# SERVER: health and logs
systemctl status career-platform nginx
sudo journalctl -u career-platform -n 50 --no-pager
```

## Teardown

Stops the AWS charges. Run only after moving the site elsewhere. Delete and terminate permissions are untested, so stop and tell Chris if one is denied. `delete-db-instance` removes automated backups, so the final snapshot below is what's kept, and it keeps billing for storage until you delete it.

```bash
aws rds modify-db-instance --db-instance-identifier career-platform-db --no-deletion-protection --apply-immediately
aws rds delete-db-instance --db-instance-identifier career-platform-db --final-db-snapshot-identifier career-platform-final
aws rds wait db-instance-deleted --db-instance-identifier career-platform-db
aws ec2 terminate-instances --instance-ids ${INSTANCE_ID}
aws ec2 wait instance-terminated --instance-ids ${INSTANCE_ID}
aws ec2 release-address --allocation-id ${EIP_ALLOC}
aws ec2 delete-security-group --group-id ${DB_SG}
aws ec2 delete-security-group --group-id ${WEB_SG}
aws ec2 delete-key-pair --key-name isba4775-aws
```

**Check:** `aws ec2 describe-instances`, `aws ec2 describe-addresses` and `aws rds describe-db-instances` show nothing still running or reserved for this project.

## Out of scope: follow-ups

- Uptime alerts. Nothing notifies you if the site goes down. A free external monitor is the simplest fix.
- Admin login on production. It needs login rate limiting first.
- Automatic deploys from GitHub. `deploy/deploy.sh` is run by hand.
- Azure cleanup. Per the README, the deallocated VM's disk and IP still bill until `rg-career-platform` is deleted. Once `www` has moved, nothing depends on it.
- Reducing `isba-student`'s permissions after the build.
