# GovReach AI frontend

React + TypeScript + Vite application for the graduation project. The current
implementation contains an Arabic RTL layout, welcome page, backend health
check, and read-only paginated campaign list. Creation, editing, generation,
history, source, and review screens are planned in
[Phase 4](PHASE_4.md).

## Development

Use Node.js 24 and npm. From this directory:

```powershell
npm ci
npm run dev
```

Open http://localhost:5173. Run FastAPI separately on http://localhost:8000.
The API client defaults to that backend URL. To override it, copy `.env.example`
to `.env.local`, set `VITE_API_BASE_URL`, and restart Vite. This URL is public.
Never put provider keys in browser code. The backend allows the frontend origin
`http://localhost:5173`; use that address rather than `127.0.0.1`.

Routes: `/` and `/campaigns` (optional `?page=2`). The list shows existing
campaigns without modifying them. Previous/Next uses the API's `skip`/`limit`;
an exactly full final page can lead to an empty next page because there is no
total count. The health indicator checks process responsiveness, not the database.
The English interface switch is a later increment; campaign language is independent.

## Verification

```powershell
npm run lint
npm test
npm run build
```

Lint checks application source and Vite configuration, excluding dependencies.
Build includes TypeScript checking and produces ignored output in dist.
API tests use Node's built-in runner with mocked fetch; no backend, database,
or Gemini calls are made. Use Node 24 as in CI.
See the [project README](../README.md) for backend setup and scope.
