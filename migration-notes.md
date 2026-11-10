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

## Log

- **2026-11-04:** Tasks 2 and 3 done: security groups, SSH key, Elastic IP, EC2 `t3.micro`, RDS `db.t3.micro` (PostgreSQL 18.6, Single-AZ, private, encrypted). Confirmed the account is on the free plan.
- **2026-11-09:** Task 1 done: privacy page names AWS and a 30-day log retention (new test), `deploy/` files added, `.env.example` comment updated. Railway's public database address refused connections again.
