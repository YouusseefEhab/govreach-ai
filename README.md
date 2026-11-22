# MarketPilot AI

[![CI](https://github.com/YouusseefEhab/govreach-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/YouusseefEhab/govreach-ai/actions/workflows/ci.yml)

MarketPilot AI is a graduation-project prototype for an AI-powered marketing
agency platform for small businesses. The current workflow manages traffic-safety
awareness campaigns and generates drafts in Egyptian Arabic and English.
Generated content stays in draft until reviewed. Approval does not publish it or
imply government endorsement.

## Current capabilities

- Campaign CRUD with pagination and validation.
- Five-field text packages in Egyptian Arabic, English, or both.
- Curated WHO summaries supplied to generation, with stored source provenance.
- Generation history and original campaign/request snapshots.
- Partial editing and independent approval/rejection of each language.
- Edited packages reset to draft for another review.

The React frontend provides an English/Arabic interface with RTL layout in Arabic.
It supports campaign creation and listing, text generation, history, draft editing,
and review. Images, video, authentication, publishing, and cloud deployment are
future milestones.

## Legacy GovReach identifiers

- Docker retains `govreach-postgres` and `govreach-redis`. Local PostgreSQL
  retains the `govreach` database and user and their matching development
  credentials so existing environments and connection strings still work.
- CI retains the `govreach_test` PostgreSQL user and database. The CI badge
  still points to the existing `YouusseefEhab/govreach-ai` GitHub repository.
- The archived graduation plan, Phase 3 evaluation, Phase 4 plan, and original
  seal files retain the former branding as project history. The existing
  `/logo.png` URL still serves the original seal for direct references. The
  storage diagnostic retains its original label on its rolled-back test row.

## Technology and architecture

| Area | Stack |
| --- | --- |
| API | Python 3.12, FastAPI, Pydantic |
| Database | PostgreSQL 16, SQLAlchemy, Alembic |
| AI | Google Gemini API and official Python SDK |
| Frontend | React, TypeScript, Vite |
| Verification | pytest, API diagnostics, build/lint |

```mermaid
flowchart LR
  UI[React frontend] --> API[FastAPI routes]
  API --> Services[Services]
  Services --> Repos[Repositories]
  Repos --> DB[(PostgreSQL)]
  Services --> Sources[Curated source catalogue]
  Services --> Adapter[Gemini adapter]
  Adapter --> Gemini[Gemini API]
```

Redis is provisioned for future work; the current synchronous text pipeline does
not use a background worker.

## Local setup

Install Python 3.12, Node.js 24, npm, and Docker Desktop with Linux containers.
From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis
```

Copy the example only on a fresh checkout; preserve an existing `.env`. Add your
own `GEMINI_API_KEY` and replace the example JWT secret. Compose credentials are
development examples, not deployment secrets.

Start the backend:

```powershell
cd backend
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt -c constraints.txt
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Open [API documentation](http://localhost:8000/docs). On Linux/macOS use
`python3.12 -m venv .venv` and `.venv/bin/python`. Runtime dependencies are in
`requirements.txt`; `constraints.txt` records the tested development environment.

In another terminal, start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open [the frontend](http://localhost:5173). Use `localhost` to match the existing
backend CORS origin. The browser does not need a Gemini key.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Application responsiveness |
| GET / POST | `/api/v1/campaigns` | List/create campaigns |
| GET / PATCH / DELETE | `/api/v1/campaigns/{id}` | Read/edit/delete campaign |
| POST | `/api/v1/campaigns/{id}/generate-text` | Generate and save drafts |
| GET | `/api/v1/campaigns/{id}/contents` | Read generation history |
| GET / PATCH | `/api/v1/contents/{id}` | Read/edit/review package |

Campaign deletion also removes its generated content. Generation uses the stored
campaign language. Legacy traffic-safety requests supply an audience and can set
the tone:

```json
{
  "audience": "السواقين والركاب في مصر",
  "tone": "informative"
}
```

Marketing campaigns accept `{}` to use the stored target audience. An explicit
`audience` overrides it for that draft. Remove pasted credentials such as API
keys, authorization tokens, and private keys from campaign text before generating.
The API rejects obvious credential patterns with HTTP 422 before sending the
input to the provider or saving a generation. Pattern matching can miss secrets.

Store approved prices, percentage promotions, and explicit guarantee terms in the
offer summary. The API rejects drafts with certain unsupported amounts,
promotions, and guarantees with HTTP 502 and saves no packages from that request.
The checks cover common EGP and USD formats and selected English and Arabic
phrases. They cannot verify all claims, phrasing, or offer conditions. Human
review is still required before publication.

Structured budget fields stay out of marketing prompts and snapshots. Budget
details pasted into free text may still be sent to the provider or saved in a
snapshot. Keep internal budgets out of the brief and other generation inputs.

Provider failures return controlled errors. A lost client connection does not
prove server cancellation; inspect saved history before submitting again.

## Verification

```powershell
# From backend: isolated tests, with no live Gemini calls
.venv/Scripts/python.exe -m pytest -q

# Optional PostgreSQL checks using temporary records and a fake provider
.venv/Scripts/python.exe -m alembic check
.venv/Scripts/python.exe -m scripts.check_generation_api

# From frontend
npm run lint
npm run build
```

Live diagnostics are opt-in. Add `--live` to
`scripts.check_generation_api` for one provider request or run
`scripts.evaluate_text_generation --live` for three. Quotas/charges depend on API
project billing. Diagnostic rows are rolled back; captured IDs are not persistent.

### Isolated PostgreSQL integration tests

The default pytest run uses SQLite. The optional PostgreSQL mode runs the same
nine marketing scenarios against a pre-created local database named
`marketpilot_integration_test`. Each test upgrades its own uniquely named
schema through Alembic, checks the revision, and removes that schema afterward.
The tests use a fake text provider.

For one-time setup in PowerShell, run the following against the existing
`govreach-postgres` container. The read-only catalog check confirms the
maintenance connection, the development database, and the absence of the test
database before creation.

```powershell
$marketPilotDatabaseCheck = docker exec govreach-postgres psql -X -w -U govreach -d postgres -v ON_ERROR_STOP=1 -At -c "SELECT current_database(), current_user, EXISTS (SELECT FROM pg_database WHERE datname = 'govreach'), EXISTS (SELECT FROM pg_database WHERE datname = 'marketpilot_integration_test');"
if ($LASTEXITCODE -ne 0 -or $marketPilotDatabaseCheck -ne 'postgres|govreach|t|f') {
    throw "Database setup stopped. Confirm the connection and check for an existing test database."
}
docker exec govreach-postgres psql -X -w -U govreach -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE marketpilot_integration_test WITH OWNER govreach TEMPLATE template0;"
if ($LASTEXITCODE -ne 0) { throw "Could not create the dedicated test database." }
```

If the name already exists, stop the setup and confirm that it belongs to this
test workflow before using it. The test runner never creates or drops the
database itself.

From `backend`, supply the local PostgreSQL login password when prompted.
The URL template is
`postgresql+psycopg://govreach:<encoded-password>@127.0.0.1:5432/marketpilot_integration_test`.

```powershell
try {
    $marketPilotTestPassword = Read-Host 'Local PostgreSQL password for govreach' -AsSecureString
    $marketPilotTestEncoded = [Uri]::EscapeDataString([Net.NetworkCredential]::new('', $marketPilotTestPassword).Password)
    $env:MARKETPILOT_TEST_DATABASE_URL = "postgresql+psycopg://govreach:${marketPilotTestEncoded}@127.0.0.1:5432/marketpilot_integration_test"
    .venv/Scripts/python.exe -m pytest -q --postgres-integration tests/test_marketing_integration.py
} finally {
    Remove-Item Env:MARKETPILOT_TEST_DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Variable marketPilotTestPassword, marketPilotTestEncoded -ErrorAction SilentlyContinue
}
```

PostgreSQL mode requires the separate test URL with a loopback host, explicit
user and port, and the exact test database name. Query parameters and other
database names are rejected. The workflow verifies the database and schema on
the server before migrating and scopes cleanup to the schema created by the test.

## Evaluation and limitations

The three-topic pilot produced six structurally valid bilingual drafts. Every
topic required editorial corrections. Sources record supplied context, not
automatic sentence-level verification. See the [pilot report](backend/PHASE_3_EVALUATION.md)
for measured durations, raw evidence, proposed corrections, and limitations.
The review was Codex-assisted, not an independent human benchmark.

Never commit real credentials, private campaign data, or production exports.

## Documentation

- [Documentation index](docs/README.md)
- [Phase 2: campaign CRUD](backend/PHASE_2.md)
- [Phase 3: text generation and review](backend/PHASE_3.md)
- [Phase 3: pilot evaluation](backend/PHASE_3_EVALUATION.md)
- [Phase 4: frontend plan](frontend/PHASE_4.md)
- [Contribution guide](CONTRIBUTING.md)
- [Security guidance](SECURITY.md)

No project license has been selected. Do not assume an open-source license from
the repository's visibility.
