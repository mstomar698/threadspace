# ThreadSpace - frontend

Next.js (App Router) + TypeScript + Tailwind v4 client for the ThreadSpace API.

## Setup

```bash
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at the Django API
npm run dev
```

The app expects the Django API running at `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`). Start the backend from the repo root first.

## Scripts

- `npm run dev` - dev server
- `npm run build` - production build (also typechecks)
- `npm run lint` - ESLint

## Structure

- `src/lib` - API client (JWT + refresh), types, query hooks
- `src/providers` - TanStack Query + auth context
- `src/components` - UI primitives, app shell, feed/post/comment components
- `src/app/(auth)` - login / register
- `src/app/(app)` - protected feed, profile, search
