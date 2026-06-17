#!/usr/bin/env bash
# Boots the real Django backend for Playwright e2e: fresh sqlite DB, migrated,
# seeded, with the GitHub network calls stubbed (GITHUB_STUB=1) so the stack
# runs end-to-end without touching github.com.
set -euo pipefail

cd "$(dirname "$0")/../.."   # repo root

PORT="${E2E_BACKEND_PORT:-8001}"
PY="${E2E_PYTHON:-.venv/bin/python}"
[ -x "$PY" ] || PY="python"

export DJANGO_SETTINGS_MODULE="backend.settings"
export DEBUG="True"
export SECRET_KEY="e2e-insecure-secret-key"
export GITHUB_STUB="1"
export GITHUB_OAUTH_CLIENT_ID="e2e-client-id"
export GITHUB_OAUTH_CLIENT_SECRET="e2e-client-secret"
export FRONTEND_URL="http://127.0.0.1:${E2E_FRONTEND_PORT:-3100}"
export CORS_ALLOWED_ORIGINS="http://127.0.0.1:${E2E_FRONTEND_PORT:-3100},http://localhost:${E2E_FRONTEND_PORT:-3100}"
export DATABASE_URL="sqlite:///$(pwd)/e2e.sqlite3"

rm -f e2e.sqlite3
"$PY" manage.py migrate --noinput
"$PY" manage.py seed_e2e
exec "$PY" manage.py runserver "127.0.0.1:${PORT}" --noreload
