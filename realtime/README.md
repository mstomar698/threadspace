# ThreadSpace realtime gateway

A small, high-throughput Rust service (axum + tokio) that powers ThreadSpace's
live feed. It does two jobs:

1. **GitHub webhook ingestion** — receives GitHub webhooks, verifies the
   `X-Hub-Signature-256` HMAC, and turns published releases / pushes into
   activity events.
2. **Real-time fan-out** — accepts events from the Django backend (which owns
   the social graph and computes each post's follower audience) and delivers
   them to connected browsers over WebSocket.

Keeping this as a separate service means the delivery path stays fast and
non-blocking even under load, and the Django request that creates a post never
waits on socket I/O.

```
GitHub ──webhook──▶ ┌────────────────────┐
                    │  realtime gateway  │◀──/internal/publish── Django (fan-out)
Browser ──WS /ws──▶ │  (axum + tokio)    │
                    └────────────────────┘
                              │ (optional)
                          Redis pub/sub  ── other gateway instances
```

## Endpoints

| Method | Path                | Purpose                                                            |
| ------ | ------------------- | ------------------------------------------------------------------ |
| GET    | `/health`           | Liveness probe.                                                    |
| GET    | `/ws?user=<name>`   | WebSocket stream. The optional `user` targets follower fan-out.    |
| POST   | `/internal/publish` | Trusted event injection (Django). Auth via `X-Internal-Token`.     |
| POST   | `/webhooks/github`  | GitHub webhook receiver. Auth via `X-Hub-Signature-256`.           |

### Event shape

All events delivered over the socket share one JSON shape:

```json
{
  "type": "post.created",
  "actor": "alice",
  "title": "shipped a new feature",
  "url": "https://github.com/alice/proj/releases/tag/v1.0.0",
  "repo": "alice/proj",
  "post_id": "0f4e...",
  "created_at": "2026-06-01T12:00:00+00:00"
}
```

`POST /internal/publish` wraps it with an optional audience:

```json
{ "audience": ["follower1", "follower2"], "event": { "type": "post.created", "...": "..." } }
```

When `audience` is omitted (or `null`), the event is broadcast to every
connected client. Webhook-sourced events are always broadcast.

## Running locally

```bash
cd realtime
cp .env.example .env   # optional; sensible defaults are built in
cargo run
# listening on 0.0.0.0:8080
```

Smoke test it:

```bash
# publish an event (no INTERNAL_TOKEN set => no auth required)
curl -X POST localhost:8080/internal/publish \
  -H 'content-type: application/json' \
  -d '{"event":{"type":"post.created","actor":"alice","title":"hi"}}'
```

## Configuration

See [.env.example](.env.example). All values are optional for local dev.

| Variable                | Default        | Notes                                            |
| ----------------------- | -------------- | ------------------------------------------------ |
| `HOST` / `PORT`         | `0.0.0.0:8080` | Bind address.                                    |
| `GITHUB_WEBHOOK_SECRET` | _unset_        | When set, webhook signatures are verified.       |
| `INTERNAL_TOKEN`        | _unset_        | When set, `/internal/publish` requires it.       |
| `REDIS_URL`             | _unset_        | Multi-instance fan-out (needs `--features redis`).|
| `RUST_LOG`              | `info`         | `tracing` filter.                                |

## Multi-instance fan-out (optional)

A single instance uses an in-memory Tokio broadcast channel. To run several
instances behind a load balancer, build with the `redis` feature and set
`REDIS_URL`; each instance subscribes to a shared Redis channel and relays
events to its own connected sockets.

```bash
cargo run --features redis
```

## Tests

```bash
cargo test
```

Covers HMAC signature verification, GitHub payload parsing (releases / pushes /
ignored events), audience routing, and hub delivery.
