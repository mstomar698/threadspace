# Contributing to ThreadSpace

Thanks for your interest in contributing! ThreadSpace is a build-in-public
social network for the open-source world, and contributions of all kinds —
code, docs, bug reports, ideas — are welcome.

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a bug** or **request a feature** via [issues](../../issues) (templates provided).
- **Improve docs** — the README, [docs/PLAN.md](docs/PLAN.md), or inline docs.
- **Pick up an issue** — comment first so we can avoid duplicate work.

## Project layout

| Path          | What it is                                                        |
| ------------- | ----------------------------------------------------------------- |
| `core/`       | Django domain models, admin, and the legacy template views        |
| `api/`        | Versioned Django REST Framework API (serializers, views, perms)   |
| `backend/`    | Django project settings and URL config                            |
| `frontend/`   | Next.js + TypeScript + Tailwind web client                        |
| `realtime/`   | Rust (axum + tokio) webhook ingestion + live-feed WebSocket gateway |
| `docs/`       | Roadmap and design notes                                          |

## Development setup

See the [README](README.md) for full setup. The fastest path is
`docker compose up --build`. To work on a single service:

### Backend (Python / Django)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

### Frontend (Next.js / TypeScript)

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Realtime gateway (Rust)

```bash
cd realtime
cargo run
```

## Before you open a pull request

Please make sure the relevant checks pass locally. CI runs all of these.

| Service   | Lint / format                              | Tests / build         |
| --------- | ------------------------------------------ | --------------------- |
| Backend   | `ruff check .` and `ruff format --check .` | `pytest`              |
| Frontend  | `npm run lint`                             | `npm run build`       |
| Realtime  | `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check` | `cargo test` |

Also run `python manage.py makemigrations --check --dry-run` if you touched models.

## Commit & PR conventions

- Use **small, focused commits** with clear messages. We loosely follow
  [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
  `docs:`, `test:`, `refactor:`, `chore:`, optionally scoped (e.g. `feat(api): ...`).
- Keep PRs scoped to one logical change; describe the *why*, not just the *what*.
- Add or update tests for behavior changes, and update docs when relevant.
- Fill out the pull request template and link any related issue.

## Reporting security issues

Please **do not** open public issues for security vulnerabilities. See
[SECURITY.md](SECURITY.md) for how to report them privately.
