# MarketPilot AI frontend

React + TypeScript + Vite application with English and Arabic interfaces and RTL
layout for Arabic. The current workflow covers traffic-safety campaign creation
and listing, text generation, draft history and sources, editing, and review.
See the [Phase 4 plan](PHASE_4.md) for the original frontend scope.

## Development

Use Node.js 24 and npm. From this directory:

```powershell
npm ci
npm run dev
```

Open http://localhost:5173. Run FastAPI separately on http://localhost:8000.
The API client defaults to that backend URL and reads `VITE_API_BASE_URL` when
configured. Never put provider keys in browser code.

## Verification

```powershell
npm run lint
npm run build
```

Lint checks application source and Vite configuration, excluding dependencies.
Build includes TypeScript checking and produces ignored output in dist.
See the [project README](../README.md) for backend setup and scope.
