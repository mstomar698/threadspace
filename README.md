# ThreadSpace

A build-in-public social network for the open-source world. Developers share devlog
posts that can attach real GitHub artifacts (repos, releases, commits, PRs), follow
people and projects, and discover what others are shipping.

This started as a first-year Django social-media clone and is being scaled into a
properly engineered, full-stack project. See [docs/PLAN.md](docs/PLAN.md) for the roadmap.

## Tech

- Backend: Django 5 + Django REST Framework (JWT, OpenAPI)
- Frontend: Next.js + TypeScript + Tailwind
- Realtime/ingestion: Rust gateway (axum + tokio) in [realtime/](realtime/)
- Data: Postgres (SQLite for local dev), optional Redis for multi-instance fan-out

## Run the whole stack with Docker

The fastest way to bring up everything (Postgres, Redis, Django API, Rust
realtime gateway, Next.js frontend):

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- API + Swagger docs: http://localhost:8000/api/docs/
- Realtime gateway: http://localhost:8080/health

It runs with zero config using dev defaults. To override secrets (e.g. a real
`SECRET_KEY`, `INTERNAL_TOKEN`, `GITHUB_API_TOKEN`, `GITHUB_WEBHOOK_SECRET`),
put them in a root `.env` or your shell before running compose.

Create an admin user once the stack is up:

```bash
docker compose exec backend python manage.py createsuperuser
```

To develop a single service without Docker, follow the steps below.

## Local setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements-dev.txt

cp .env.example .env   # then edit values

python manage.py migrate
python manage.py runserver
```

Defaults to a local SQLite database. Set `DATABASE_URL` in `.env` to use Postgres.

## API

A versioned REST API (Django REST Framework, JWT auth) is available under `/api/`:

- `POST /api/v1/auth/register/` - create an account
- `POST /api/v1/auth/token/` + `/api/v1/auth/token/refresh/` - obtain/refresh JWT
- `GET|PATCH /api/v1/auth/me/` - current user's profile
- `/api/v1/profiles/` - list/search profiles; `/{username}/`, `/{username}/follow/`, `/followers/`, `/following/`
- `/api/v1/posts/` - CRUD; `/feed/` (cursor-paginated, followed users + self); `/{id}/like/`
- `/api/v1/comments/?post={id}` - comments (with light threading via `parent`)

Interactive docs (Swagger UI): `/api/docs/`. OpenAPI schema: `/api/schema/`.

## Frontend

A Next.js + TypeScript + Tailwind client lives in [frontend/](frontend/). Run the
Django API first, then:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev   # http://localhost:3000
```

For local dev, set `DEBUG=True` in the backend `.env` so uploaded media is served.

## Realtime gateway (Rust)

A separate Rust service ([realtime/](realtime/)) ingests GitHub webhooks and
delivers live activity to the feed over WebSocket. The web app works without it;
set `REALTIME_URL` (backend) and `NEXT_PUBLIC_REALTIME_URL` (frontend) to enable
the live feed.

```bash
cd realtime
cargo run        # listening on 0.0.0.0:8080
cargo test
```

When the gateway is running, creating a post fans the event out to the author's
followers and the feed shows a live "new updates" pill. See
[realtime/README.md](realtime/README.md) for endpoints and configuration.

## Development

```bash
ruff check .          # lint
ruff format .         # format
pytest                # run tests
```

Configuration is environment-driven (see `.env.example`). Never commit your `.env`.
