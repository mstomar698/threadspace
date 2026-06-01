# Scale ThreadSpace into an Open-Source Build-in-Public Social Platform

> Living roadmap. Phase 0 is in progress. Deployment (Oracle Always Free tier) is deferred.

## The product angle (unique, not Reddit, not Instagram)

ThreadSpace becomes a **social network for the open-source world** - a "build in public" feed for developers and the projects they work on.

What makes it distinct:

- **Identity- and project-centric**, not topic/community + voting (that's Reddit). You follow _people_ and _projects/repos_, not "subreddits".
- Posts ("devlogs") can **attach real GitHub artifacts** - a repo, release, commit, PR, or issue - which get auto-enriched (title, language, stars) via the GitHub API.
- **Project pages**: contributors, tech-stack tags, an activity timeline, "follow this project".
- **Connect your GitHub** (OAuth): import repos, optionally auto-post new releases via webhooks.
- Reactions + light threaded comments, a personalized feed, and a contribution/activity graph.

This keeps the social primitives we already have (profiles, posts, follow, likes) but reframes them around OSS work.

## Recommended stack (Python + TS + Rust)

```mermaid
flowchart LR
  user["Browser"] --> fe["Next.js + TS frontend"]
  fe -->|REST + JWT| api["Django REST Framework API (Python)"]
  api --> pg[("Postgres")]
  api --> redis[("Redis cache/queue")]
  gh["GitHub webhooks"] --> rust["Rust ingestion + feed fan-out + WS gateway"]
  rust --> redis
  rust --> pg
  fe -.->|"WebSocket (live feed)"| rust
```

- **Backend API**: Django + Django REST Framework (Python) - clean models, JWT auth, OpenAPI docs, pytest tests.
- **Frontend**: Next.js + TypeScript + Tailwind - modern, polished UI replacing the static UIkit templates.
- **Rust service**: high-throughput GitHub webhook ingestion + activity-feed fan-out + a WebSocket gateway for the live feed (axum + sqlx + redis).
- **Infra (local only for now)**: Postgres + Redis via `docker-compose`. Deployment to Oracle free tier deferred.

## Phase 0 - Foundations and cleanup (in progress)

- Rewrite `core/models.py` with real relationships: `Post.user` as `ForeignKey`, timezone-aware `auto_now_add`, `Like`/`Follow` with `ForeignKey`s + unique constraints, DB indexes.
- Replace the Python `chain()` feed loop in `core/views.py` with a single ORM query.
- Move `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/database config to env via `django-environ`.
- Fix the unsafe like-via-GET (`/like-post`) to POST.
- Modernize deps: Django 4.2 -> 5.x, clean `requirements.txt`, add `pyproject.toml`.
- Tooling: `ruff`, `pytest` + `pytest-django` + `factory_boy`, GitHub Actions CI, `.env.example`. Fill in `core/tests.py`.

## Phase 1 - Django REST Framework API (done)

- Added DRF, SimpleJWT, drf-spectacular, django-cors-headers.
- Architecture decision: kept domain models in `core` and added a dedicated, versioned `api`
  app for the REST layer (serializers/views/permissions/pagination). Avoids risky cross-app
  model relocation with no current payoff; can still split later.
- Added a `Comment` model (light threading via `parent`).
- Serializers + ViewSets + router under `/api/v1/`: register, JWT token/refresh, `me`,
  profiles (+ follow/followers/following), posts (CRUD + cursor-paginated `feed` + `like`),
  comments, search. OpenAPI schema at `/api/schema/`, Swagger UI at `/api/docs/`.
- 24 tests passing (auth, permissions, feed scoping, like/follow toggles, comments, search).

## Phase 2 - Next.js + TypeScript frontend (core app done)

- Built `frontend/` (Next.js 16 App Router, TS, Tailwind v4, TanStack Query) with a
  dark-first, GitHub/Linear-style design system.
- JWT auth (token store + transparent refresh), typed fetch client, auth context.
- Screens: login/register with route guards, infinite-scroll feed + composer, post cards
  with optimistic likes and inline comments, profile pages with follow/stats, user search.
  Production build + typecheck + lint all green.
- Remaining/optional: retire the old Django templates once the SPA fully replaces them;
  generate the typed client directly from the OpenAPI schema; richer profile editing.

## Phase 3 - GitHub integration (core differentiator done)

- `Repo` model caching enriched GitHub metadata (stars, forks, language, topics, etc.),
  plus an optional `Post.repo` link so devlogs can reference a project.
- GitHub enrichment service ([core/github.py](../core/github.py)): parses URLs/`owner/name`,
  fetches from the public GitHub API (optional `GITHUB_API_TOKEN`), and caches with a TTL.
- API: `POST /api/v1/github/resolve/`, `GET /api/v1/github/repos/<owner>/<name>/`,
  attach a repo on post create via `repo_full_name`, and `GET /posts/?repo=owner/name`.
- Frontend: composer "Repo" attach with live preview, repo cards on posts, and project
  pages at `/projects/[owner]/[name]` listing the project's devlogs.
- Remaining/optional: GitHub OAuth "Connect GitHub" + repo import (needs an OAuth app /
  secrets, so deferred); auto-posting releases via webhooks lands in Phase 4 (Rust).

## Phase 4 - Rust service + real-time (polyglot standout)

- Rust service (axum + sqlx + redis): webhook ingestion (signature-verified), feed fan-out via Redis, WebSocket live-feed endpoint for the Next.js feed.

## Notes / deferred

- Deployment out of scope for now (Oracle Always Free tier later, not Railway); `docker-compose` stays local-only.
- Keep everything OSS - no proprietary SaaS dependencies.
- Keep the repo runnable at the end of every phase.
