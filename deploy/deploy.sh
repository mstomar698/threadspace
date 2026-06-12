#!/usr/bin/env bash
# Pull the latest main and (re)deploy the production stack on the VM.
# Run from the repository root: ./deploy/deploy.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env.production ]]; then
  echo "Missing .env.production (copy .env.production.example and fill it in)." >&2
  exit 1
fi

git fetch --all
git reset --hard origin/main

# include any host-local compose overlays (e.g. a co-located app)
files=(-f docker-compose.prod.yml)
for f in docker-compose.*.local.yml; do [ -e "$f" ] && files+=(-f "$f"); done

docker compose "${files[@]}" --env-file .env.production up -d --build
docker image prune -f

echo "Deployed. Tail logs with:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
