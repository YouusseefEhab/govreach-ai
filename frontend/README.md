# GovReach AI frontend

React + TypeScript + Vite application for the graduation project. The current
implementation contains a welcome page and backend health check. Campaign,
generation, history, source, editing, and review screens are planned in
[Phase 4](PHASE_4.md).

## Development

Use Node.js 24 and npm. From this directory:

```powershell
npm ci
npm run dev
```

Open http://localhost:5173. Run FastAPI separately on http://localhost:8000.
The API client currently uses that backend URL. Configurable frontend API settings
are part of Phase 4. Never put provider keys in browser code.

## Verification

```powershell
npm run lint
npm run build
```

Lint checks application source and Vite configuration, excluding dependencies.
Build includes TypeScript checking and produces ignored output in dist.
See the [project README](../README.md) for backend setup and scope.
