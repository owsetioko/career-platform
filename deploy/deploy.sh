#!/usr/bin/env bash
# Deploy the latest code on the EC2 server. Run as ubuntu: bash /opt/career-platform/deploy/deploy.sh
set -euo pipefail

APP_DIR=/opt/career-platform

sudo -u career sh -c "cd $APP_DIR && git pull --ff-only && uv sync --locked --no-dev && .venv/bin/python -m app.database"
sudo systemctl restart career-platform
sleep 3

# A 200 isn't enough: the app serves a fallback page when the database is unreachable.
page=$(curl -fsS http://127.0.0.1:8000/)
if ! grep -q 'Chris Owen Setioko' <<<"$page"; then
    echo "deploy check failed: profile name missing from the home page" >&2
    exit 1
fi
if grep -qE 'temporarily unavailable|Your Name' <<<"$page"; then
    echo "deploy check failed: home page is showing the fallback or starter profile" >&2
    exit 1
fi
echo "deploy ok"
