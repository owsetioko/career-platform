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
| 2026-11-09 | 7 | One certificate, for `csetioko.me` and `www`, after the DNS change | A separate certificate for `aws.csetioko.me`, issued now, with its own Nginx server block (`deploy/nginx-career-platform.conf`) | Chris asked for HTTPS on the `aws` name. A separate block keeps the Task 7 certificate from replacing this one. | Two certificates to renew instead of one; Certbot's timer renews both. Certbot's edits to the live Nginx file aren't in the repo copy, so re-copying `deploy/nginx-career-platform.conf` to the server would drop HTTPS until `certbot --nginx` is rerun. |
| 2026-11-09 | 7 | Step 3: Chris changes the two records by hand in the Cloudflare dashboard | Changed with the Cloudflare CLI (`cf dns records update`), after a dry run, overwriting each record in place | Chris asked for the cutover to be done for him; the CLI also leaves before/after snapshots. | None. Old values are in `backups/cloudflare-dns-pre-cutover.json` for rollback. |
| 2026-11-09 | 8 | Wait 48 quiet hours after cutover; close Railway's database proxy and update README and docs before merging | Merged and redeployed from `main` right after cutover; README and docs left for the course guide's section 12 step; the Railway proxy left for Chris (the service is down anyway) | Chris asked to merge now, and Railway is down, so a push to `main` can't disturb a live site. | No quiet period to catch problems before `main` changes, though the site was verified in Task 7. README still describes Railway until section 12. |
| 2026-11-09 | 8 | Server pulls from GitHub | Server's `origin` repointed from the git bundle to GitHub, then switched to `main` | Follows the Task 1 ruling. | None. |

## Log

- **2026-11-04:** Tasks 2 and 3 done: security groups, SSH key, Elastic IP, EC2 `t3.micro`, RDS `db.t3.micro` (PostgreSQL 18.6, Single-AZ, private, encrypted). Confirmed the account is on the free plan.
- **2026-11-09:** Task 1 done: privacy page names AWS and a 30-day log retention (new test), `deploy/` files added, `.env.example` comment updated. Railway's public database address refused connections again.
- **2026-11-09:** **csetioko.me found down.** Every path on Railway returns `404 Application not found` (`x-railway-fallback: true`), and the Railway database's public address closes connections. Cause not confirmed (likely trial credit or a paused service). The plan's rollback to Railway may no longer work.
- **2026-11-09:** Tasks 4 and 5 done: server packages (Postgres 18.6 client, Nginx, Certbot, uv), swap, 30-day logs, automatic security reboots, `career` user, code from a git bundle. RDS role and database created over verified TLS 1.3; data restored; fingerprint identical to the backup.
- **2026-11-09:** Task 6 done: app service (4 processes, all as `career`) and Nginx running; the app's own connection is `career_app` over TLS; `deploy/deploy.sh` passed and left the data identical; site correct from outside via the server's IP; port 8000 and RDS unreachable from outside; survived a reboot.
- **2026-11-09:** Task 7 Step 1: mail records saved to `backups/mail-before.txt` (Zoho MX ×3, SPF, Zoho verification, DMARC, DKIM). Waiting on Chris for the Cloudflare change.
- **2026-11-09:** Added `aws.csetioko.me` (A, DNS only) with the Cloudflare CLI. Before/after snapshots of all records show 10 → 11 records, nothing removed or changed. It resolves on Cloudflare's own servers and on 1.1.1.1, and `http://aws.csetioko.me/` serves the profile from AWS.
- **2026-11-09:** Let's Encrypt certificate for `aws.csetioko.me` (expires 2027-02-08), HTTP → HTTPS redirect (301). From outside: HTTPS 200 with a verified certificate over TLS 1.3, profile shown, no fallback. `csetioko.me` and `www` behave as before.
- **2026-11-09:** Tested `https://aws.csetioko.me` from outside and on the server: all pages, static files and redirects as expected (admin 503 because it's off; unknown paths 404); 20/20 home page loads were 200, averaging 0.33 s from California; all 26 visible database items appear on the page; no fallback; snapshot file written; logs record visitors' real IP addresses, matching the privacy page; no tracebacks; memory 467 of 909 MB used.
- **2026-11-09, 05:20 UTC: cutover.** `csetioko.me` CNAME (Railway) → A record to the Elastic IP; `www` A (old Azure IP) → the Elastic IP; both DNS only. Exactly two records changed (11 before and after). Cloudflare's nameservers and the public resolvers (1.1.1.1, 8.8.8.8) returned the new IP within about 12 seconds. Let's Encrypt certificate for `csetioko.me` + `www` (expires 2027-02-08), after a successful dry run. Checks: home page shows the real profile with no fallback; HTTP and `www` redirect to `https://csetioko.me`; `Server: nginx`, no Railway headers; mail records identical to `backups/mail-before.txt`; both certificates pass `certbot renew --dry-run`; no errors in the app log. The site was down on Railway before this, so there was no extra HTTPS gap. Still for Chris: an email round-trip to `chris@csetioko.me`, and the padlock in a browser.
- **2026-11-09:** Merged `aws-ec2-rds-migration` into `main` and redeployed the server from `main` (see Task 8 rows).

## Course guide section 10: verify on a test subdomain (checked 2026-11-09)

| Guide step | Result | Evidence |
| --- | --- | --- |
| A record `aws` → Elastic IP, DNS only, via the Cloudflare CLI | Pass | `cf dns records list`: one A record for `aws.csetioko.me`, pointing at the Elastic IP, `proxied: false` (grey cloud). The other 10 records are byte-for-byte the same as the snapshot taken before the change, including the 2 Railway records and 7 mail records. |
| `nslookup aws.csetioko.me` answers with the Elastic IP | Pass | The laptop's own resolver returns the Elastic IP. |
| Let's Encrypt certificate and HTTP → HTTPS redirect | Pass | `http://` returns `301` to `https://`. The certificate is from Let's Encrypt (`YE2`) for `aws.csetioko.me` only, valid until 2027-02-08; `openssl` verifies the chain (return code 0) over TLS 1.3. `certbot renew --dry-run` succeeded and `certbot.timer` is active. |
| The app works at `aws.csetioko.me` | Pass | Home and privacy pages `200`, with the real profile and no fallback warning or placeholder. CSS, JS and fonts `200`. Admin `503` (off by design); unknown paths `404`. All 26 visible database items appear on the page. 20/20 loads `200`, averaging 0.33 s. The app's database connection uses TLS as `career_app`. Logs record real visitor IPs, matching the privacy page. Survived a reboot (Task 6). |

**Not verified yet:**
- The two visual checks the guide asks Chris to do himself: the record in the Cloudflare dashboard, and the padlock in a browser. The same facts were checked from the CLI and `openssl`.
- What visitors see if RDS becomes unreachable. The fallback page exists, but the outage test wasn't run.
- A real certificate renewal. Only the dry run has run; the first real renewal is due around January 2027.
- Phones or browsers other than `curl`, and traffic beyond 20 requests in a row.
- IPv6. The server has no IPv6 address and there's no AAAA record, so IPv6-only visitors can't reach it.
- **The guide's premise that Railway keeps serving the real domain no longer holds.** `csetioko.me` returns Railway's `404 Application not found` (`x-railway-fallback: true`), so the main domain is down until the cutover in section 11.
