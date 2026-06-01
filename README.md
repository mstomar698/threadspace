# ThreadSpace

A build-in-public social network for the open-source world. Developers share devlog
posts that can attach real GitHub artifacts (repos, releases, commits, PRs), follow
people and projects, and discover what others are shipping.

This started as a first-year Django social-media clone and is being scaled into a
properly engineered, full-stack project. See [docs/PLAN.md](docs/PLAN.md) for the roadmap.

## Tech (current + planned)

- Backend: Django 5 (Django REST Framework API in Phase 1)
- Frontend: Next.js + TypeScript (Phase 2)
- Realtime/ingestion: Rust service (Phase 4)
- Data: Postgres (SQLite for local dev), Redis

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

## Development

```bash
ruff check .          # lint
ruff format .         # format
pytest                # run tests
```

Configuration is environment-driven (see `.env.example`). Never commit your `.env`.
