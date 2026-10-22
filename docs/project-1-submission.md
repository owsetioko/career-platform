# Project 1 submission

| | |
| --- | --- |
| Repository | https://github.com/owsetioko/career-platform |
| Live site (HTTPS) | https://csetioko.me/ |
| Privacy page | https://csetioko.me/privacy |
| Final commit SHA | The commit on `main` that merges this file, "Merge branch 'railway-postgres-migration'" right after "docs: add Project 1 submission". The full SHA is in the Brightspace submission; a commit can't contain its own SHA. The previous deployed commit was `f6646cb6a75fd70ceef4c786f28394fc75404b87`. |

Checks marked "2026-10-21" were run from my laptop on 2026-10-21 (Pacific),
23:16 PDT (06:16 UTC on 2026-10-22).

## 1. README, spec, and plans

- [README](../README.md)
- [Application spec](specs/personal-resume-platform-spec.md)
- [Application plan](plans/personal-resume-platform-plan.md)
- Deployment plans:
  - [Azure VM migration](superpowers/plans/2026-09-24-azure-vm-migration.md) (2026-09-24)
  - [Operate the VM: systemd + Nginx](superpowers/plans/2026-10-01-operate-the-vm.md) (2026-10-01)
  - [Railway + PostgreSQL migration](superpowers/plans/2026-10-08-railway-postgres-migration.md) (2026-10-08)

## 2. Diagrams

All in [architecture.md](architecture.md):

- [Before: Azure VM](architecture.md#before-azure-vm-2026-10-07-to-2026-10-08)
- [Now: Railway + PostgreSQL](architecture.md#now-railway--postgresql-since-2026-10-08)
- [Email data flow (Zoho)](architecture.md#email-zoho-mail-on-csetiokome)
- [Analytics data flow (GA4)](architecture.md#analytics-google-analytics-4-opt-in)

## 3. Migration plans and source/target data comparisons

### Laptop → Azure VM (SQLite → SQLite)

Plan: [Azure VM migration](superpowers/plans/2026-09-24-azure-vm-migration.md).
Comparison: [Verify results](superpowers/plans/2026-09-24-azure-vm-migration.md#verify-results).
The laptop and VM database files had the same SHA-256 (`da926cf2…74dbd`),
and the page showed `Chris Owen Setioko` with 0 placeholder strings.

### Azure VM → Railway (SQLite → PostgreSQL)

Plan: [Railway + PostgreSQL migration](superpowers/plans/2026-10-08-railway-postgres-migration.md).

| | Source: SQLite (VM and laptop) | Target: Railway PostgreSQL |
| --- | --- | --- |
| Fingerprint | VM and laptop `.dump` hashes identical, `8989f2cf…` ([inspection findings](superpowers/plans/2026-10-08-railway-postgres-migration.md#inspection-findings-2026-10-08)) | n/a |
| profiles / experiences / skills / projects | 1 / 5 / 15 / 3 | 1 / 5 / 15 / 3 ✓ |
| project tags | 0 | 0 ✓ |
| education | 3 | 3 ✓ |
| experience-skill / project-skill links | 8 / 4 | 8 / 4 ✓ |
| Name on the live page | `Chris Owen Setioko` | `Chris Owen Setioko`, 0 × `Your Name` (2026-10-21) |

The target counts were not written down during the copy, so they were
re-counted on 2026-10-21 with a `count(*)` query in the Railway dashboard
(Postgres → Database → Data): screenshots
[1](evidence/railway-postgres-counts-1.png) and
[2](evidence/railway-postgres-counts-2.png). All 8 tables match the source.
Together with the identical source fingerprints and the real name on the
live page, this shows the copy moved every row.

## 4. Migration cutover and rollback

Cutover steps and rollback path: [Railway plan → Task 5](superpowers/plans/2026-10-08-railway-postgres-migration.md#task-5-move-csetiokome-to-railway-operational).
Rollback is to point `csetioko.me` back to `20.88.61.1` in Cloudflare, with
the VM's Nginx and certificate left untouched.

Results:

- **Apex cut over.** The DNS snapshot from 2026-10-13 shows
  `CNAME csetioko.me → tbtcq5cj.up.railway.app` and the
  `_railway-verify` TXT record ([dns-before-zoho.md](evidence/dns-before-zoho.md#records)).
  The certificate now served for `csetioko.me` was issued 2026-10-08
  21:23 UTC, the same day as the cutover (section 6).
- **`www` was not cut over.** It is still `A www.csetioko.me → 20.88.61.1`,
  and on 2026-10-21 the VM no longer answered: HTTPS and HTTP on `www` both
  timed out. See [section 9](#9-failures-decisions-reflection-costs-and-limitations).
- **Rollback was not needed** and was not rehearsed. On 2026-10-21,
  `az vm show -d` reported the VM as **deallocated** (stopped, no compute
  charges) with its static IP `20.88.61.1` still reserved. Its disk, Nginx
  config, and certificate are intact. Rollback is still possible, but it
  now needs `az vm start` (about 2 minutes) before switching DNS back.

## 5. Azure HTTP and restart evidence

- HTTP from outside: [operate the VM → Task 5](superpowers/plans/2026-10-01-operate-the-vm.md#task-5-verify-from-the-outside-about-3-min).
  `200` and the name at `http://20.88.61.1/`, `Server: nginx/1.24.0 (Ubuntu)`,
  and port 8000 timed out (blocked).
- Restart: [operate the VM → Record](superpowers/plans/2026-10-01-operate-the-vm.md#record).
  The VM rebooted at 10:24 UTC on 2026-10-07 and `career-platform` was active
  again by 10:24:10 without anyone starting it. `Restart=always` on the app and
  `Restart=on-failure` on Nginx, with both `enabled`.
- The VM at its public IP: [Ex03](evidence/ex03.md) and
  [screenshot](evidence/ex03-site.png).
- HTTPS on the VM: [How this site is secured](how-this-site-is-secured.md)
  (Let's Encrypt, Certbot renewal, open ports). That write-up describes the VM
  and is out of date for Railway.
- **Crash test: not run.** The plan lists a crash test (kill the service
  and watch systemd bring it back), but I didn't run it before the cutover.
  The VM has been deallocated since moving to Railway. Restart recovery is
  shown by the reboot above and by the unit's `Restart=always` setting, not
  by a deliberate crash.

## 6. Final DNS and HTTPS verification (2026-10-21)

```
$ dig +short csetioko.me
69.46.46.84
$ dig +short www.csetioko.me
20.88.61.1

$ openssl s_client -connect csetioko.me:443 -servername csetioko.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
subject= /CN=csetioko.me
issuer= /C=US/O=Let's Encrypt/CN=YE2
notBefore=Oct  8 21:23:52 2026 GMT
notAfter=Jan  6 21:23:51 2027 GMT
Subject Alternative Name: DNS:csetioko.me

$ curl -Iv https://csetioko.me/          # certificate part; run 2026-10-22 07:17 UTC
* Connected to csetioko.me (69.46.46.84) port 443
* SSL connection using TLSv1.3 / AEAD-CHACHA20-POLY1305-SHA256
* Server certificate:
*  subject: CN=csetioko.me
*  start date: Oct  8 21:23:52 2026 GMT
*  expire date: Jan  6 21:23:51 2027 GMT
*  subjectAltName: host "csetioko.me" matched cert's "csetioko.me"
*  issuer: C=US; O=Let's Encrypt; CN=YE2
*  SSL certificate verify ok.

$ curl -sI https://csetioko.me/
HTTP/2 405            # HEAD isn't allowed; GET returns the page
server: railway-hikari
x-railway-edge: lax1

$ curl -s https://csetioko.me/ | grep -o "<title>[^<]*"
<title>Chris Owen Setioko | Information Systems &amp; Business Analytics Student, Loyola Marymount University
$ curl -s https://csetioko.me/ | grep -c "Your Name"
0
$ curl -s -o /dev/null -w "%{http_code}\n" https://csetioko.me/static/css/styles.css
200
$ curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" http://csetioko.me/
301 -> https://csetioko.me/
$ curl -s -o /dev/null -w "%{http_code}\n" https://www.csetioko.me/
000                   # timed out: www still points at the old VM
```

The apex is served by Railway (`server: railway-hikari`) over a valid
certificate, and HTTP redirects to HTTPS. The certificate covers only
`csetioko.me`, not `www`.

## 7. A reviewed commit, its Railway deployment, and live verification

Railway deploys every push to `main` and reports each one to GitHub as a
deployment to `independent-expression / production`.

| | |
| --- | --- |
| Commit | [`1ae97af`](https://github.com/owsetioko/career-platform/commit/1ae97afa1cf8107ae2dbcc95b8da1d2f124b3216) "fix: link static assets with root-relative paths" (adds a test in `tests/test_app.py`) |
| Merged to `main` | [`9419c74`](https://github.com/owsetioko/career-platform/commit/9419c74), 2026-10-20 00:05 PDT |
| Railway deployment | GitHub deployment for `9419c74`: `success` at 2026-10-20 07:10:54 UTC, replaced (`inactive`) by the next deploy at 07:22:10 UTC |
| Live verification (2026-10-21) | `curl -s https://csetioko.me/ \| grep -o 'href="[^"]*styles.css[^"]*"'` → `href="/static/css/styles.css"` (root-relative, the change itself), and the stylesheet returns `200`. Before the fix, the href was an absolute `http://` URL that browsers blocked as mixed content. |

The current production deploy is `f6646cb` (`success` at 2026-10-20
08:21:27 UTC), and GitHub's commit status for `main` is `success`.

Review evidence:

- **Tests at the commit itself.** `uv run python -m pytest -q` on a checkout
  of `1ae97af`: 75 passed, 3 skipped. The skips are the Postgres
  integration tests, which run only when `TEST_DATABASE_URL` is set. The
  commit adds `test_static_asset_urls_are_root_relative`, which asserts that
  pages link `href="/static/css/styles.css"` and contain no absolute
  `://…/static` URL. On current `main` the suite is 77 passed, 3 skipped
  (2026-10-21).
- **Live check after deploy.** See the table above.
- **My review.** I read the diff (5 templates and 1 new test) and, after
  Railway deployed it, checked that the live page loaded with its CSS. The
  repo has no pull requests, so this review isn't recorded on GitHub.

## 8. Zoho Mail and Google Analytics

### Email (Zoho)

- Sending, receiving, and replying: [Ex06 → Email tests](evidence/ex06.md#1-email-tests)
- SPF, DKIM, and DMARC authentication: [Ex06 → Authentication results](evidence/ex06.md#2-authentication-results)
  and the full [Zoho header check](evidence/zoho-header-check.md)
- DNS before the Zoho records were added: [dns-before-zoho.md](evidence/dns-before-zoho.md)

DNS on 2026-10-21: `MX 10 mx.zoho.com`, `20 mx2.zoho.com`, `50 mx3.zoho.com`.
`TXT "v=spf1 include:zohomail.com ~all"`,
`_dmarc "v=DMARC1; p=none; rua=mailto:chris@csetioko.me"`, and a DKIM key
at `zmail._domainkey`.

### Analytics (GA4)

- Evidence: [Ex06 → Google Analytics](evidence/ex06.md#3-google-analytics),
  with screenshots of [page_view and click in Realtime](evidence/ex06-ga4-events.png)
  and [the click event's parameters](evidence/ex06-ga4-click.png)

How it works: the site shows a consent banner, and
[`consent.js`](../app/static/js/consent.js) doesn't request Google's
`gtag.js` until the visitor clicks Accept. After that, GA4 records a
`page_view` for each page load. It also records a `click` when the visitor
follows a link to another site, such as the GitHub link. That event comes
from GA4's enhanced measurement and carries `link_domain`, `link_url`, and
`outbound=true`. Declining means nothing is sent. The
[privacy page](https://csetioko.me/privacy) explains this to visitors, and
the [analytics diagram](architecture.md#analytics-google-analytics-4-opt-in)
shows the flow. The screenshots come from my own browser after accepting,
because a visitor who declines is never counted.

## 9. Failures, decisions, reflection, costs, and limitations

### Failures

- Azure region and VM size not allowed on the student subscription:
  [Ex03 → What went wrong](evidence/ex03.md#3-what-went-wrong-and-how-i-fixed-it).
- SSH blocked after my IP changed: [Ex03 → The change](evidence/ex03.md#4-the-change).
- DNS/TLS failure investigation (simulation): [Ex05](evidence/ex05.md).
- Postgres blockers found before the move (psycopg2 URL, boolean default,
  `http://` asset URLs): [Railway plan → Inspection findings](superpowers/plans/2026-10-08-railway-postgres-migration.md#inspection-findings-2026-10-08).
- Unstyled page on Railway (mixed content): fixed in `1ae97af` and
  `5395819`. It was diagnosed with a temporary commit (`680abec`), which was
  then reverted (`b8225af`).
- Failed Railway deployment of `1d212a2` on 2026-10-13: "Railpack failed
  to prepare the build". Railway's diagnosis was a config error: it detected
  a Python app but found no start command
  ([screenshot](evidence/railway-failed-deploy-2026-10-13.png)). At that
  point `main` had no `railway.json`, because the Railway config was still
  on the `railway-postgres-migration` branch and wasn't merged until
  `0b185ca` later that day. The build stopped before deploy, so the
  previous deployment kept serving the site. Fix: I applied Railway's
  suggested start command from that page, and the service's Settings →
  Deploy → Custom Start Command is still
  `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`. The next
  deploy, `b92bb26`, succeeded.
- `www.csetioko.me` was left pointing at the old VM (section 4).

### Decisions

- [Azure VM plan → Decisions](superpowers/plans/2026-09-24-azure-vm-migration.md#decisions-made-while-writing-this-plan)
- [Operate the VM → Decisions](superpowers/plans/2026-10-01-operate-the-vm.md#decisions)
- [Railway plan → Global Constraints](superpowers/plans/2026-10-08-railway-postgres-migration.md#global-constraints)
  covers deploying only from GitHub `main`, keeping the VM as the rollback,
  keeping admin disabled, and accepting an ephemeral snapshot instead of a
  volume.
- GA4 is opt-in, so it loads only after Accept ([privacy page](https://csetioko.me/privacy)).

### Reflection

[README → Reflection](../README.md#reflection).

### Costs

[README → Costs](../README.md#costs). In short: about $4.70 of Azure student
credit (mostly the static public IP and the disk; VM compute was $0), $0.54
of Railway usage on the Trial plan ($5 one-time credit), and $0 for the domain (Namecheap) and Zoho
Mail, both through the GitHub Student Pack. No card has been charged.

### Remaining limitations

- `www.csetioko.me` doesn't work: it points at the old VM, and Railway's
  certificate covers only the apex.
- Admin is disabled in production (no `SESSION_SECRET` or `ADMIN_PASSWORD_HASH`).
- The page snapshot lives on the container's disk and is wiped on every
  deploy, so if Postgres is down right after a deploy, visitors see the
  starter profile ("Your Name").
- DMARC is `p=none`: failures are reported, not blocked
  ([Zoho header check](evidence/zoho-header-check.md#what-it-shows)).
- [How this site is secured](how-this-site-is-secured.md) still describes
  the VM (Certbot, NSG ports, TLS ending at Nginx).
- Leftover Azure resources (NIC, NSG, public IP, disk) haven't been cleaned
  up. The disk and public IP still bill against student credit.
- Railway is on the Trial plan with a one-time $5 credit. Keeping the site
  up long-term needs the paid Hobby plan.
- Production runs the start command set in the Railway dashboard
  (`uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`; Railway sets
  `PORT=8080`), which overrides the one in `railway.json`. Proxy trust is
  therefore handled in app code plus the `FORWARDED_ALLOW_IPS` variable
  instead of the `--proxy-headers` flag. Deploy config now lives in two
  places that can drift apart.
