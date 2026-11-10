# Migration notes: Railway → AWS (EC2 + RDS)

Running log for [the migration plan](docs/superpowers/plans/2026-11-04-aws-ec2-rds-migration.md).
Every place the real run differs from the plan is recorded here, with why and what it costs.
This repo is public, so no IP addresses, account IDs, passwords or resource IDs go in this file.

## Deviations from the plan

| Date | Task | Plan said | What happened | Why | Cost or risk |
| --- | --- | --- | --- | --- | --- |
| 2026-11-04 | 3 | RDS backup retention 7 days | 1 day | The account is on the AWS free plan, which rejected 7 days (`FreeTierRestrictionError`). The plan allowed this fallback. | Point-in-time restore covers only about the last day. Local dumps in `backups/` are the longer-term copy. |
| 2026-11-04 | 2 | Set a passphrase on the SSH key | No passphrase | Claude runs the server steps and can't answer a passphrase prompt. | Anyone with the key file on the laptop can reach the server. Add one after setup: `ssh-keygen -p -f ~/.ssh/isba4775_aws`. |
| 2026-11-04 | 2, 3 | Task 2 fully before Task 3 | RDS was created after only the two security groups; the key, web ports and IP came with the EC2 launch | Chris asked for the database first, and it needed only the groups. | None. |
| 2026-11-09 | 1, 4 | Push the branch to GitHub, after checking in Railway that only `main` deploys; the server clones it from GitHub | Not pushed. The server gets the branch as a `git bundle` file copied over SSH | Avoids any chance of a Railway redeploy and doesn't need the Railway check before cutover. | The server's `origin` points at the bundle until Task 8, which repoints it to GitHub before `git pull`. |
| 2026-11-09 | 5 | Take a fresh Railway dump and fingerprint Railway directly | Restored the 2026-11-02 backup; the fingerprint came from restoring that file locally | Railway is down (see Log) and its database's public address drops every connection. The 2026-11-02 dump matched Railway exactly on 2026-11-04, and admin was off in production, so the data couldn't change. | If anything did change on Railway after 2026-11-04, it isn't in RDS. Admin being off makes that very unlikely. |
| 2026-11-09 | 7 | Step 2: re-fingerprint Railway just before the DNS change | Skipped | Railway is down and its database refuses connections. RDS already matches the last verified Railway data, and admin was off. | Same as the Task 5 row. |
| 2026-11-09 | 7 | Change only the `csetioko.me` and `www` records, by hand in the Cloudflare dashboard | Added a third record first: `aws.csetioko.me` A → the server's Elastic IP, DNS only, using the Cloudflare CLI (`cf dns records create`) | Chris asked for a separate name that reaches the AWS server. | One more public name that points at the server. It answers over HTTP only until a certificate covers it. |

## Log

- **2026-11-04:** Tasks 2 and 3 done: security groups, SSH key, Elastic IP, EC2 `t3.micro`, RDS `db.t3.micro` (PostgreSQL 18.6, Single-AZ, private, encrypted). Confirmed the account is on the free plan.
- **2026-11-09:** Task 1 done: privacy page names AWS and a 30-day log retention (new test), `deploy/` files added, `.env.example` comment updated. Railway's public database address refused connections again.
- **2026-11-09:** **csetioko.me found down.** Every path on Railway returns `404 Application not found` (`x-railway-fallback: true`), and the Railway database's public address closes connections. Cause not confirmed (likely trial credit or a paused service). The plan's rollback to Railway may no longer work.
- **2026-11-09:** Tasks 4 and 5 done: server packages (Postgres 18.6 client, Nginx, Certbot, uv), swap, 30-day logs, automatic security reboots, `career` user, code from a git bundle. RDS role and database created over verified TLS 1.3; data restored; fingerprint identical to the backup.
- **2026-11-09:** Task 6 done: app service (4 processes, all as `career`) and Nginx running; the app's own connection is `career_app` over TLS; `deploy/deploy.sh` passed and left the data identical; site correct from outside via the server's IP; port 8000 and RDS unreachable from outside; survived a reboot.
- **2026-11-09:** Task 7 Step 1: mail records saved to `backups/mail-before.txt` (Zoho MX ×3, SPF, Zoho verification, DMARC, DKIM). Waiting on Chris for the Cloudflare change.
- **2026-11-09:** Added `aws.csetioko.me` (A, DNS only) with the Cloudflare CLI. Before/after snapshots of all records show 10 → 11 records, nothing removed or changed. It resolves on Cloudflare's own servers and on 1.1.1.1, and `http://aws.csetioko.me/` serves the profile from AWS.
