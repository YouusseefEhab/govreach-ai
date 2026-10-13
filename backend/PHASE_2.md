# Phase 2: campaign API verification

Inspected and tested on 2026-10-12.

## Existing implementation

The request flow is routes -> services -> repositories -> SQLAlchemy -> database.
All five CRUD operations were already implemented. No layers or database tables
were replaced. The initial Alembic revision is `851ce324628e`.

| Endpoint | Successful response | Behavior |
| --- | --- | --- |
| POST /api/v1/campaigns | 201 | Create a draft campaign |
| GET /api/v1/campaigns | 200 | List newest first; skip >= 0, limit 1–100 |
| GET /api/v1/campaigns/{id} | 200 | Fetch one campaign; missing ID returns 404 |
| PATCH /api/v1/campaigns/{id} | 200 | Update supplied non-null fields; missing ID returns 404 |
| DELETE /api/v1/campaigns/{id} | 204 | Empty response; missing ID returns 404 |

Creation defaults: domain `traffic_safety`, language `both`, status `draft`.
Supported languages: `arabic`, `english`, `both`. Status updates currently only
accept `draft`. Custom domains remain accepted, preserving the existing contract.
Empty or null-only PATCH requests remain successful no-ops.

## Changes and automated verification

- Added pytest configuration and development test dependencies.
- Added 26 API tests for CRUD, Arabic text, all languages, defaults, pagination,
  missing records, input validation, partial updates, health, and OpenAPI routes.
- Trimmed surrounding whitespace in create/update schemas so blank titles,
  domains, and objectives fail with 422. Internal whitespace is preserved.
- Added a connection timeout and main guard to the existing database diagnostic.
  Importing it no longer opens a database connection.

From `backend`, run:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

Result: **26 passed**. Tests use a fresh in-memory SQLite database for every test
and override `get_db`; development PostgreSQL data is never modified. This
verifies HTTP behavior through the real routes, services, and repositories, but
does not verify PostgreSQL connectivity, deployed HTTP, or Alembic migration state.
The installed Starlette emits a TestClient/httpx deprecation warning. Tests pass;
dependency migration should be handled separately after compatibility testing.

PostgreSQL diagnostic failed and `docker compose ps` reported that the Docker
Desktop Linux engine pipe was unavailable. PostgreSQL integration is pending.
The `/health` endpoint only checks application responsiveness; it does not check
database availability.

## Step-by-step local PostgreSQL and Swagger verification

1. Start Docker Desktop with its Linux engine. From the project root:

   ```powershell
   docker compose up -d postgres redis
   docker compose ps
   ```

2. From `backend`, check the database and migration revision:

   ```powershell
   .venv/Scripts/python.exe test_database.py
   .venv/Scripts/python.exe -m alembic current
   .venv/Scripts/python.exe -m alembic heads
   ```

   Both revision commands should show `851ce324628e`. If the database is behind,
   apply the existing migration with `.venv/Scripts/python.exe -m alembic upgrade head`.
   Do not recreate the table or run a downgrade on existing campaign data.

3. Start the server if it is not already running:

   ```powershell
   .venv/Scripts/python.exe -m uvicorn app.main:app --reload
   ```

4. Open http://127.0.0.1:8000/docs. Use POST with this disposable campaign:

   ```json
   {
     "title": "Phase 2 test - seat belt awareness",
     "domain": "traffic_safety",
     "objective": "Encourage drivers and passengers to wear seat belts",
     "language": "both"
   }
   ```

   Expect 201, an integer ID, `draft`, and a creation timestamp. Record that ID.

5. GET the ID, then GET the list with `skip=0` and `limit=20`. Expect 200 and the
   created campaign. PATCH only `{"title": "اربط حزام الأمان"}`; expect 200 and
   the objective and language to remain unchanged.

6. POST with `language: "french"`, or a whitespace-only title, and request the
   list with `limit=101`. Each should return 422.

7. DELETE only the disposable campaign ID. Expect 204 with no body. GET, PATCH,
   and DELETE that same ID afterward should return 404. Do not delete pre-existing
   campaigns during this check.

Phase 2 CRUD acceptance is complete when the automated suite passes and this
PostgreSQL-backed walkthrough succeeds. Authentication, deployment, and generated
media persistence are separate follow-up work, not verified by this test suite.

## AI pipeline proposal — pending architectural confirmation

No AI endpoints, providers, generated-content tables, or job queues have been added.

Proposed first increment: **text generation** for existing campaigns, with one
Arabic result and one English result when `language` is `both`.

Proposed flow:

1. `POST /api/v1/campaigns/{id}/generate-text` loads the campaign and validates a
   request containing audience, tone, and output format.
2. A generation service builds a versioned prompt from the campaign objective,
   language, and approved traffic-safety source material.
3. A provider adapter calls an API-based LLM with explicit timeouts and bounded
   retries. Tests replace the adapter with a fake; they never incur provider costs.
4. Validate structured output and persist each language variant in a separate
   `generated_contents` table linked to the campaign by a foreign key.
5. Return draft content for human review. Generation must not publish a campaign
   automatically. Avoid unsupported legal or statistical claims; capture the
   source references used in generation.

Proposed storage fields: ID, campaign ID, content type, language, text or media
storage key, provider, model, prompt version, source references, review status,
and UTC creation timestamp. The exact schema and campaign deletion behavior need
agreement before a new Alembic migration is written.

For the first text-only increment, use a synchronous request with a timeout if
acceptable. Images and videos should follow as separate increments, using cloud
object storage for assets and background jobs with job-status endpoints for long
operations. Redis exists in Compose, but no queue worker is implemented today.

Decisions to confirm before implementation: the separate generated-content table
and provider-adapter boundary; then select a provider/model, approved source
material, review rules, and cloud storage/queue approach when needed.
