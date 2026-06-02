---
name: threadspace-checks
description: >-
  Run ThreadSpace's lint, test, and build checks across the Django backend,
  Next.js frontend, and Rust realtime gateway. Use before committing, when asked
  to test/verify/check the project, or after changing code in core/, api/,
  backend/, frontend/, or realtime/.
---

# ThreadSpace checks

Verify changes per service. For a scoped change, run only the affected
service's checks; before a commit/release or a "test everything" request, run
all three. CI mirrors these exactly (`.github/workflows/ci.yml`).

## Backend (Python / Django) — repo root

Activate the venv first (`.venv\Scripts\Activate.ps1` on Windows,
`source .venv/bin/activate` otherwise), then:

```bash
ruff check .
ruff format --check .
python manage.py makemigrations --check --dry-run   # only if models changed
python manage.py check
pytest
```

## Frontend (Next.js / TypeScript) — in `frontend/`

```bash
npm run lint
npm run build        # also runs the TypeScript typecheck
```

Note: `next build` does NOT fail on ESLint errors, so always run `npm run lint`
separately.

## Realtime gateway (Rust) — in `realtime/`

On Windows the GNU toolchain needs MinGW on `PATH`. Prepend it for the session:

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;C:\Users\tomar\AppData\Local\Microsoft\WinGet\Packages\BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe\mingw64\bin;$env:Path"
```

Then:

```bash
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

Run `cargo fmt` (no `--check`) to auto-fix formatting before committing.

## Pass criteria

- Backend: ruff clean, no migration drift, `pytest` green.
- Frontend: `npm run lint` clean, `npm run build` succeeds.
- Realtime: fmt clean, clippy emits no warnings (`-D warnings`), `cargo test` green.

If anything fails, fix it and re-run that service's checks before moving on.
