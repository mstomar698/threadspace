# ThreadSpace — agent guide

A build-in-public social network for the open-source world. Polyglot monorepo:
Django REST API (Python), Next.js frontend (TypeScript), and a Rust realtime
gateway. Read [docs/PLAN.md](docs/PLAN.md) for the roadmap and [CONTRIBUTING.md](CONTRIBUTING.md)
for the contributor workflow.

## Architecture

- `core/` — Django domain models (`Profile`, `Post`, `Like`, `Follow`, `Comment`,
  `Repo`), admin, GitHub enrichment (`core/github.py`), and the realtime publish
  helper + `post_save` fan-out signal (`core/realtime.py`, `core/signals.py`).
- `api/` — versioned DRF API under `/api/v1/` (serializers, viewsets,
  permissions, pagination). JWT auth, OpenAPI via drf-spectacular.
- `backend/` — Django settings (12-factor via `django-environ`) and URLs.
- `frontend/` — Next.js App Router + TypeScript + Tailwind v4 + TanStack Query.
  Has its own [AGENTS.md](frontend/AGENTS.md) — heed it (this Next.js differs from
  training data; check `node_modules/next/dist/docs/`).
- `realtime/` — Rust (axum + tokio) gateway: GitHub webhook ingestion +
  WebSocket live-feed fan-out. In-memory hub by default; optional Redis bridge
  behind `--features redis`.

## Conventions

- **Commits**: small, focused, Conventional Commits (`feat:`, `fix:`, `docs:`,
  `test:`, `refactor:`, `chore:`, optionally scoped). Commit with the author
  email `tomarm698@gmail.com`. Only commit/push when the user asks.
- **Keep the repo runnable** at the end of every change.
- Config is environment-driven; never commit `.env`. See the `.env.example`
  files. Features degrade gracefully when optional services are unset
  (`REALTIME_URL`, `GITHUB_API_TOKEN`, `REDIS_URL`).

## Running checks

Run the relevant service's checks after changes (all three before a release).
The `threadspace-checks` skill has the full matrix and commands.

| Service  | Lint / format                              | Tests / build   |
| -------- | ------------------------------------------ | --------------- |
| Backend  | `ruff check .`, `ruff format --check .`    | `pytest`        |
| Frontend | `npm run lint` (in `frontend/`)            | `npm run build` |
| Realtime | `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings` (in `realtime/`) | `cargo test` |

If you touch models: `python manage.py makemigrations --check --dry-run`.

## Gotchas

- **Tests run with `DEBUG=False`**: security hardening (SSL redirect, HSTS,
  secure cookies) is opt-in via env vars, defaulting off, so tests/dev are safe.
  Don't gate behavior on `DEBUG` for those.
- **Querysets must stay ordered** for DRF pagination — aggregations (`Count`)
  can strip the `ordered` flag, so add an explicit `.order_by(...)`.
- **Rust on Windows**: the toolchain here is the GNU target; builds need MinGW on
  `PATH`. Prepend cargo + the WinLibs `mingw64\bin` dir before `cargo` commands.
- **`lucide-react` has no `Github` brand icon** — use `GitBranch` etc.
- The legacy Django templates (`templates/`, `core/views.py`) coexist with the
  Next.js SPA and are slated for retirement; prefer the `api/` + `frontend/`.
