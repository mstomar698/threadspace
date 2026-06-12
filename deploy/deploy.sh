#!/usr/bin/env bash
# (Re)deploy the production stack on the VM. Run from the repo root on the VM:
#   ./deploy/deploy.sh
#
# Code is delivered to the VM by the GitHub Actions deploy workflow (rsync from
# the runner) or by a manual rsync; this script only (re)builds and brings the
# stack up. It auto-includes any host-local compose overlays for co-located apps
# (docker-compose.*.local.yml), and Caddy imports any deploy/sites/*.caddy.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env.production ]]; then
  echo "Missing .env.production (copy .env.production.example and fill it in)." >&2
  exit 1
fi

files=(-f docker-compose.prod.yml)
for f in docker-compose.*.local.yml; do [ -e "$f" ] && files+=(-f "$f"); done

docker compose "${files[@]}" --env-file .env.production up -d --build
docker image prune -f

echo "Deployed. Tail logs with:"
echo "  docker compose ${files[*]} logs -f"
