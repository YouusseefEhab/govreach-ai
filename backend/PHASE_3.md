# Phase 3 — AI text generation

## Progress

- Phase 2: user confirmed the PostgreSQL-backed Swagger CRUD walkthrough succeeded.
- Step 1: requirements and proposed API contract drafted on 2026-10-13.
- Arabic style: Egyptian Arabic (العامية المصرية), confirmed by the user.
- Step 2: added `app/schemas/generation.py` with request, text-package, and draft
  generation-response schemas. Added 27 schema tests; the full suite passes
  all 53 tests (26 existing API tests plus 27 schema tests).
- Step 4 architecture and cascade deletion approved by the user.
- Generated-content model, repository, and Alembic migration implemented. Migration
  `b7f23e8d10a4` applied to local PostgreSQL; `alembic check` reports no schema drift.
  Existing campaign rows/values verified unchanged using a pre/post migration hash.
- Storage-increment regression suite: 82 passed (including 19 new storage/migration tests).
  PostgreSQL storage diagnostic also passed; its temporary rows were rolled back.
- Generation and retrieval API implemented with a Gemini adapter, versioned
  prompt, controlled provider errors, and persisted response metadata.
- Current regression suite: 165 passed. New PostgreSQL API checks with a fake
  provider also passed. Live API diagnostic outcome is recorded below.
- Draft editing/review endpoint implemented and verified against PostgreSQL.
- The user confirmed campaign 7's live generation and retrieval succeeded, with
  Arabic content ID 9 and English content ID 10.
- User confirmed editing and approval worked in Swagger.
- Curated WHO source sections are now selected, supplied to generation, and
  snapshotted in stored references.
- Phase 3 backend implementation and three-topic pilot evaluation are complete.
  See `PHASE_3_EVALUATION.md` for results and limitations. All six live drafts
  passed structural checks; each topic needed qualitative edits before approval.
- Gemini account/key created by the user. Added private key configuration and a
  standalone development diagnostic using Google's official `google-genai` SDK.
  Full regression suite: 63 passed; automated tests make no provider requests.
  Provider adapter and generation/retrieval routes are now implemented.
- Live Gemini diagnostic: the initial attempt returned HTTP 503. The user then
  reran the diagnostic successfully and shared structurally valid Egyptian Arabic
  and English packages. Connectivity is verified by the user's reported run.
  This establishes one successful sample, not a full quality/model evaluation.

## Step 3: Gemini connection diagnostic

The application reads the existing project-root `.env` (one directory above
`backend`). Add these settings while preserving its database and other entries:

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=90
```

The key is a Pydantic `SecretStr`, masked when settings are represented or
serialized. `.env` is already ignored by Git. Keep the actual key out of source,
chat, screenshots, and logs.

From `backend`, run:

```powershell
.venv/Scripts/python.exe -m scripts.check_gemini
```

This makes one generation attempt with retries disabled, using a fixed generic
seat-belt prompt. It requests an Egyptian Arabic and an English text package,
validates both against `TextPackage`, and prints the sample for human review.
It does not query PostgreSQL or save campaign content. Provider exception details
are suppressed so credentials and response bodies are not printed on failure.
Successful structural validation does not establish dialect or factual quality.

Google's [quickstart and structured-output examples](https://ai.google.dev/gemini-api/docs/get-started)
were used for the SDK integration. The configured model is a development candidate,
not a completed comparative model evaluation. Check your account's model access
and quotas in AI Studio. Google's [pricing page](https://ai.google.dev/gemini-api/docs/pricing)
lists free-tier access for this model; the project billing tier determines charges.

Dependency changes: added `google-genai==2.30.1` and updated the `google-auth` pin
to `2.62.0` to satisfy the SDK. Converted `requirements.txt` from UTF-16 to UTF-8,
preserving other dependency entries. `pip check` reports no broken requirements
in the installed environment. Existing Starlette/httpx deprecation warning remains.

## Step 1: proposed requirements

Initial domain: traffic safety. Existing campaign CRUD continues accepting its
current domain values; the new generation feature initially supports only
`traffic_safety`.

Generate a text package containing five nonempty fields:

| Field | Purpose | Proposed maximum characters |
| --- | --- | --- |
| headline | Main campaign heading | 120 |
| slogan | Short memorable phrase | 100 |
| awareness_message | Brief explanation of the campaign objective | 1200 |
| social_caption | Ready-to-review social post | 600 |
| call_to_action | Concrete action for the audience | 200 |

These are application limits, not claims about social-platform limits. Validate
them after generation; do not truncate output silently.

Language comes from the existing campaign. `arabic` produces one Arabic package,
`english` one English package, and `both` exactly one of each. Arabic defaults to
Egyptian Arabic (العامية المصرية), as requested by the user. Use clear,
respectful Egyptian wording suitable for public awareness campaigns. Even a
`formal` tone should retain this dialect choice. The bilingual versions should
communicate the same objective naturally, without requiring literal translation.

Audience is required. Proposed tones: `informative`, `encouraging`, `formal`, with
`informative` as the default. The first increment uses a fixed text-package format.
Selectable individual output formats can be added later.

All results begin as drafts requiring human review. Do not publish automatically
or change the campaign's existing status. Do not invent statistics, penalties,
legal requirements, or government endorsement. Treat campaign and audience text
as input data rather than instructions that override generation rules.

## Generation API contract (implemented)

`POST /api/v1/campaigns/{campaign_id}/generate-text`

Request:

```json
{
  "audience": "Drivers and passengers in Egypt",
  "tone": "informative"
}
```

Use campaign title, objective, domain, and language from the database, rather than
duplicating them in this request. Audience should be trimmed, nonempty, and at
most 300 characters. Reject unsupported tones and unexpected request fields.

Illustrative 201 response for a campaign whose language is `both`:

```json
{
  "campaign_id": 3,
  "contents": [
    {
      "id": 10,
      "language": "arabic",
      "content_type": "text_package",
      "review_status": "draft",
      "content": {
        "headline": "سلامتك بتبدأ بحزام الأمان",
        "slogan": "اربط الحزام في كل مشوار",
        "awareness_message": "خلّي ربط حزام الأمان عادة ليك ولكل اللي معاك في العربية قبل كل مشوار.",
        "social_caption": "قبل ما تتحرك، اتأكد إن كل اللي معاك رابطين حزام الأمان.",
        "call_to_action": "اربط حزامك قبل ما تبدأ المشوار."
      }
    },
    {
      "id": 11,
      "language": "english",
      "content_type": "text_package",
      "review_status": "draft",
      "content": {
        "headline": "Start every journey with a seat belt",
        "slogan": "Buckle up on every trip",
        "awareness_message": "Make fastening a seat belt a habit for everyone in the car before each journey.",
        "social_caption": "Before setting off, check that everyone has fastened their seat belt.",
        "call_to_action": "Fasten your seat belt before the journey begins."
      }
    }
  ]
}
```

This is a hand-written contract example, not output from an AI call. Persisted
responses will also need agreed metadata such as creation time and prompt version.
Schema validation checks required fields, lengths, allowed tones, language values,
and duplicate language variants. It does not establish dialect quality or factual
accuracy. The future service must ensure response languages match the campaign.

Proposed error behavior:

| Status | Situation |
| --- | --- |
| 404 | Campaign does not exist |
| 422 | Invalid audience/tone or unsupported generation domain |
| 502 | Provider returns unusable output |
| 503 | Generation provider is unavailable or not configured |
| 504 | Provider call exceeds its timeout |

On a failed bilingual request, save neither language variant. Preserve previous
generations; successful repeated calls create new drafts. A repeated request can
incur another provider charge; idempotency needs a separate decision before
automated retries are exposed to clients.

## Implementation sequence

1. Agree on the package fields, Arabic style, and contract above.
2. Add Pydantic generation request/response schemas and focused validation tests.
   This alone does not add working generation routes.
3. Select a provider/model using project-specific Arabic and English examples.
4. Review and approve the provider boundary and generated-content database design,
   including deletion behavior, before implementing adapters or migrations.
5. Prepare approved source material and versioned prompts.
6. Implement generation, output validation, atomic persistence, and retrieval.
7. Add draft editing and review endpoints without automatic publication.
8. Test with a fake provider, then run explicitly authorized real-provider checks.
9. Complete Swagger/PostgreSQL verification and a small quality evaluation report.

Phase 3 completion requires working generation, persistence, retrieval, editing,
review, controlled failures, and documented Arabic/English evaluation. Images,
videos, frontend integration, and cloud rollout follow in later increments.

## Successful sample review

The shared sample uses recognizable Egyptian phrasing: `قبل ما`, `سايق`,
`الكنبة ورا`, and `خلي`. The English package expresses the same main objective
and includes both front- and back-seat passengers. All five fields were returned
in each language and passed the diagnostic's structural validation.

Editorial adjustment before use: remove the precise duration `ثانية واحدة`
and `only a second`. Prefer `خد لحظة واربط حزامك قبل ما تتحرك` and
`Take a moment to fasten your seat belt before setting off`. Prompt rules should
discourage unsupported numeric claims, including incidental timing statements.
The output is a draft; it has not been checked against approved official sources.

## Step 4: approved architecture and completed storage increment

Preserve the existing routes -> services -> repositories pattern. Add a Gemini
provider adapter responsible only for API requests and parsing. The generation
service handles campaign lookup, prompt building, language matching, validation,
and persistence. Tests substitute a fake adapter. Keep live-provider requests out
of automated tests, and disable automatic generation retries initially.

Add `generated_contents` through a new Alembic revision, without altering campaign
columns. Store one complete five-field package per language per successful request:

| Column | Proposed storage / purpose |
| --- | --- |
| id | Integer primary key |
| campaign_id | Indexed foreign key to campaigns.id |
| generation_id | UUID grouping the language variants from one request |
| language | arabic or english; no both value on a stored package |
| content_type | text_package for this increment |
| content | JSON containing the five validated text fields |
| provider / model | Generation provider and model identifiers |
| prompt_version | Identifier for the prompt rules used |
| input_snapshot | JSON recording title, objective, domain, audience, tone, and dialect at generation time |
| source_references | JSON snapshots of references supplied to the generation prompt; empty means no references were supplied |
| review_status | draft initially; approved/rejected supported by the later review workflow |
| created_at | UTC timestamp |

Use a uniqueness constraint on `(generation_id, language)`. Save both bilingual
variants in one database transaction after both pass validation. Repeat generation
creates a new generation ID, preserving earlier drafts. Campaign edits do not
rewrite existing generated content or its input snapshot.

Approved deletion behavior: deleting a campaign also deletes its generated-content
rows through `ON DELETE CASCADE`. This preserves the existing hard-delete campaign
API, but removes the associated generation history as well. The user approved
this behavior before the migration was implemented.

The first increment is complete: model, migration, repository, and persistence
tests. The provider adapter/service and generation/retrieval routes come next, with
approved-source preparation before claiming grounded output.

### Files and verification

- `app/models/generated_content.py`: JSON text packages, request snapshots,
  generation UUIDs, metadata, review status, and UTC timestamps. Database checks
  restrict language/type/status and enforce one package per generation/language.
- `app/models/__init__.py`: registers the new model for Alembic and SQLAlchemy.
- `app/repositories/generated_content.py`: validates all language packages before
  adding records, saves them in one transaction, rolls back write failures, and
  retrieves content/history scoped to a campaign. No calls to an AI provider.
- `alembic/versions/b7f23e8d10a4_create_generated_contents_table.py`: adds only
  the generated-content table, constraints, and campaign index. Campaign columns
  are unchanged.
- `tests/conftest.py`: shared isolated database fixtures and SQLite foreign-key
  enforcement, so cascade and orphan prevention tests exercise real constraints.
- Storage tests cover language matching, Arabic JSON, bilingual writes, validation
  failures, transaction rollback/session recovery, generation history, snapshots,
  database constraints, and selective cascade deletion.
- Migration test upgrades/downgrades only a disposable SQLite file and verifies
  model/schema agreement and preservation of a pre-existing campaign.
- `scripts/check_content_storage.py`: repeatable PostgreSQL diagnostic using an
  outer transaction and savepoints. Tests bilingual storage, UTC timestamps,
  history, and cascade deletion, then rolls back all diagnostic rows. PostgreSQL
  sequence values may advance; existing campaign/content values are preserved.

From `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m alembic current
.venv/Scripts/python.exe -m alembic check
.venv/Scripts/python.exe -m scripts.check_content_storage
```

Current local PostgreSQL revision: `b7f23e8d10a4`. A fresh checkout/database needs
`.venv/Scripts/python.exe -m alembic upgrade head` before generation storage is used.
Do not downgrade the development database to repeat migration tests: downgrading
the new revision deletes generated content/history.

The storage increment made no paid/live AI calls. Existing campaign CRUD
regression tests remain passing. Generation routes were added in the next
increment described below.

## Generation and retrieval increment

The existing campaign routes are preserved. New routes under `/api/v1`:

| Route | Success | Purpose |
| --- | --- | --- |
| POST /campaigns/{campaign_id}/generate-text | 201 | Generate, validate, and save new drafts |
| GET /campaigns/{campaign_id}/contents | 200 | List history, newest first; skip/limit pagination |
| GET /contents/{content_id} | 200 | Read one persisted language package |

Provider adapter: `app/providers/gemini.py`. The `get_text_provider` dependency
allows automated tests to substitute a fake. A structured provider schema requires
exactly the campaign's language variants. Requests use the single-turn
`generateContent` method with JSON schema output, low thinking effort, a timeout,
and automatic retries disabled. No Interactions conversation is created. These
options do not change account billing or Google's applicable data-use terms.
API errors omit provider response bodies and
credentials; quota/access/unavailability returns 503, timeouts 504, and incomplete
or malformed output 502.

Service: `app/services/generation.py`. It checks campaign existence/domain before
calling Gemini, sends campaign fields as JSON data separate from fixed system
instructions, validates every language package, and saves through the repository.
Initial prompt version `traffic-text-v1` required Egyptian Arabic even for a formal tone,
and discourages invented legal/statistical claims and precise timing statements.
Prompt rules are not a guarantee of factual accuracy or resistance to adversarial
input; drafts still require human review.

The initial increment supplied no sources; its `source_references` values were
empty. The later source-catalogue increment below supplies reference snapshots.
Neither increment establishes verified official Egyptian legal guidance.

Responses include generation UUID, campaign ID, language, five-field content,
review status, provider/model, prompt version, request snapshot, source references,
and creation timestamp. Generation does not change the campaign's status. Repeated
POSTs create new history and consume another provider request. There is no
idempotency mechanism yet; avoid blindly retrying a generation request.

### Swagger walkthrough

1. Reload http://127.0.0.1:8000/docs after Uvicorn reloads (restart the server if
   running without `--reload`). Look for the **Generated Content** section.
2. Create a disposable traffic-safety campaign using the existing POST route,
   with `language` set to `both`. Record its campaign ID.
3. Expand POST `/api/v1/campaigns/{campaign_id}/generate-text`, click **Try it out**,
   enter that ID, and use this request body:

   ```json
   {
     "audience": "السواقين والركاب في مصر",
     "tone": "informative"
   }
   ```

   Click **Execute** once and wait for completion. Expect 201 with Arabic/English
   packages, one shared `generation_id`, and `review_status: draft`. Review the
   language and factual quality manually. A provider error returns a controlled
   message; a malformed bilingual result is not partially saved.
4. GET `/api/v1/campaigns/{campaign_id}/contents`; expect 200 with both saved rows.
   Copy a content `id` and GET `/api/v1/contents/{content_id}`; expect the same row.
5. Optionally generate again to verify a new generation ID and preserved history.
   This consumes another API request. Do not use existing campaigns for deletion
   tests; deleting your disposable campaign removes its generated content too.

### Repeatable PostgreSQL diagnostic

From `backend`, run:

```powershell
.venv/Scripts/python.exe -m scripts.check_generation_api
```

This uses the real app routes and PostgreSQL with a fake provider. To make one
live Gemini call instead, explicitly run:

```powershell
.venv/Scripts/python.exe -m scripts.check_generation_api --live
```

Both modes create a temporary campaign inside an outer transaction, verify
generation/retrieval/cascade deletion, and roll back diagnostic rows. Sequence
values may advance. This uses FastAPI's in-process HTTP test client; a manual
Swagger run is still useful to verify the currently running Uvicorn process.

Automated tests forbid live Gemini clients and use isolated SQLite storage.
They cover all three language selections, history, retrieval/pagination/cascade,
validation before provider calls, provider errors, malformed outputs, missing
configuration, API documentation, and sanitized SDK errors. The installed
Starlette/httpx TestClient deprecation warning remains; tests pass.

### Verification outcome for this increment

- Full automated suite: **121 passed**. Existing campaign CRUD remains passing.
- The running Uvicorn server's `/openapi.json` exposes all three new routes;
  refresh Swagger to see them.
- PostgreSQL API diagnostic with fake provider: passed generation (201), list/read
  (200), campaign deletion (204), and deleted-content lookup (404). Diagnostic
  rows were rolled back and existing database row counts remained unchanged.
- Live PostgreSQL/API/Gemini diagnostic: two attempts returned controlled 503
  responses. Safe SDK logging confirmed `InternalServerError`, HTTP 503, from
  Gemini. No generated content was saved; all temporary campaigns were rolled
  back. At that point the live success path was pending; the subsequent model
  adjustment and user's successful campaign 7 test are recorded below.
- `pip check`: no broken installed requirements. No new migration was needed
  for the generation routes.

The user subsequently completed the generation and retrieval Swagger walkthrough.
The user also completed editing/review. Source material has now been connected;
the three-topic Egyptian Arabic/English pilot evaluation is now documented in
`PHASE_3_EVALUATION.md`. Broader quality hardening remains future work.

### Timeout adjustment

The user reported a 504 from campaign 7's generation request. The configured
timeout was 45 seconds. Increased the application default and local `.env`
setting to 90 seconds to allow more time for bilingual generation. The limit
remains configurable up to 120 seconds, with automatic retries disabled. A longer
timeout does not guarantee that an unavailable provider will succeed. Restart
Uvicorn if its process has not reloaded the new settings before trying again.
Timeouts occur before persistence, so the failed generation creates no saved rows.

### Repeated 503 investigation and successful fix

The user received a 503 after the timeout increase. Read-only model checks
confirmed `gemini-3.8-flash` was available and listed `generateContent` support.
A live diagnostic using that method still returned an upstream `ServerError` 503,
so the previous Interactions method was not established as the sole cause.

Tested `gemini-3.5-flash-lite`, which the account also listed as available, using
a temporary diagnostic model override. The live PostgreSQL/API diagnostic passed:
generation 201, retrieval 200, and deletion checks 204/404. All temporary records
were rolled back. Set the local `.env` and application default model to this tested
candidate; retained the 90-second timeout and disabled automatic retries.
Model availability and one successful request do not guarantee future availability
or campaign quality; human review/evaluation remains necessary.

The adapter now uses the SDK's public `models.generate_content` method with
structured JSON output and low thinking effort, and rejects truncated outputs.
The standalone `check_gemini` diagnostic reuses this adapter to prevent its request
path drifting from the application. Existing routes, language fields, and database
schema are unchanged.

Documentation consulted: [GenerateContent API](https://ai.google.dev/api/generate-content),
[Gemini troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting), and
[thinking configuration](https://ai.google.dev/gemini-api/docs/thinking).
Safe model-availability check: `.venv/Scripts/python.exe -m scripts.check_gemini_models`.
The API diagnostic accepts `--model` for testing alternatives without editing `.env`.

## Draft editing and review increment

Added PATCH `/api/v1/contents/{content_id}` with a 200 response containing the
updated stored package. No migration is needed because review status and JSON
content storage already exist. No Gemini call is made during editing or review.

To edit only the awareness message (for example, removing a typo and safety
guarantee from the Arabic draft), replace Swagger's entire request body with:

```json
{
  "content": {
    "awareness_message": "سواء كنت سايق أو راكب جنب السواق أو في الكنبة اللي ورا، اربط حزامك قبل ما تتحرك. خلي ربط الحزام عادة في كل مشوار، وشجّع كل اللي معاك في العربية يعملوا كده."
  }
}
```

Unspecified text fields, the other language package, earlier generations, and
generation metadata are preserved. Every content edit resets this package's
status to `draft`, including edits to approved or rejected packages.

After retrieving and reviewing the edited package, use a separate PATCH to approve:

```json
{
  "review_status": "approved"
}
```

Use `rejected` to reject or `draft` to reopen a package. Approval changes the
selected package's review label; it does not publish content, approve the other
language automatically, change campaign status, or establish source verification.

Validation rejects empty/null edits, whitespace-only text, overlong fields,
unsupported statuses, metadata changes, and attempts to edit and approve/reject
in the same request. Missing content IDs return 404; database write failures
roll back and return a sanitized 503. PostgreSQL locks the selected row while
applying the update to serialize concurrent edits/review operations.

Edits update the selected package in place. Earlier generation rows remain intact,
but this increment does not create a per-edit audit trail or record reviewer
identity/time. Those require a later schema/workflow decision. The stored
`created_at` remains the generation creation timestamp.

Verification: **141 automated tests passed**, including 20 new API tests for
partial edits, metadata/history isolation, all review statuses, re-edit draft
reset, rejected invalid payloads, missing IDs, and database rollback/recovery.
The PostgreSQL diagnostic now exercises editing, approval, rejection, and draft
reset as well as generation/retrieval/deletion. It passed with a fake provider,
rolled back its test rows, and left existing row counts unchanged. The user's
campaign 7 content was not edited by this diagnostic.

Refresh Swagger and test PATCH on Arabic content ID 9, then retrieve it with
GET `/api/v1/contents/9`. Review English content ID 10 separately before approval.

## Curated traffic-safety source material

Added `app/knowledge/traffic_safety.json`, version `traffic-sources-v1`, with four
topic sections from WHO's official [Road traffic injuries fact sheet](https://www.who.int/news-room/fact-sheets/detail/road-traffic-injuries).
The page was checked on 2026-10-13. This is one official publication with four
section references, not four independent publications. Topics: seat belts,
speeding, distracted driving, and general prevention. The catalogue contains
brief project-authored summaries, without numeric statistics, Egyptian-law
interpretations, fines, or government endorsements. This is an initial prototype
allowlist; institutional approval of the catalogue is a separate process.

`app/services/traffic_sources.py` validates the catalogue and uses campaign title
and objective keywords in Arabic/English to select topical sections. Multiple
topics can be selected; an unmatched objective receives only general prevention
material. Selection is simple keyword matching, not a semantic/vector retrieval
system. Unsupported specific claims should be omitted by the prompt and checked
by the human reviewer. A missing/invalid catalogue fails closed with a controlled
503 before any AI request.

Prompt version `traffic-text-v2-sourced` sends selected reference metadata and
summaries in `source_material`. Instructions restrict factual claims to that
material, discourage guaranteed-safety language, and keep URLs in metadata rather
than inserting them into the campaign's five text fields.

Each saved language package records source ID, topic, title, publisher, URL,
section, check date, catalogue version, supplied facts, and usage marker
`supplied_to_generation_prompt`. This is provenance of the input context, not
proof that Gemini used each reference or that every sentence is supported.
Approval and structural validation do not automatically establish factual accuracy.

Source snapshots are stored using the existing JSON column; no migration or
campaign schema change was needed. Existing generations remain unchanged and
retain their original prompt version/reference values. Editing a package preserves
its original supplied-source snapshot and resets it to draft; a reviewer must
check whether the edited wording remains supported.

Verification: **159 automated tests passed**. New checks cover Arabic/English topic
matching, multiple topics, general fallback, official HTTPS source validation,
malformed catalogue rejection, immutable selection snapshots, prompt/reference
consistency, fail-closed behavior, and reference preservation after editing.
The PostgreSQL API diagnostic with a fake provider verified source persistence
and retrieval, then rolled back its temporary rows.
One live sourced-prompt diagnostic returned an upstream HTTP 504 timeout. No
generated content was saved; temporary rows were rolled back and existing counts
were unchanged. The user subsequently verified live success in Swagger, as
recorded below.

### Swagger check

Generate a new package for campaign 7 using the existing generate-text request.
Expect 201, a new generation UUID, `prompt_version: traffic-text-v2-sourced`, and
a nonempty `source_references` list containing `who-seat-belts`. GET the new
content ID to check those references were persisted. Earlier content IDs 9/10
are not retroactively assigned source references. Review and approve new drafts
separately; approval of the older packages does not apply to the new generation.

The final planned Phase 3 step was a documented quality evaluation; that pilot
has now been completed and is linked below.

### User-confirmed sourced generation and retrieval

The user shared a successful 201 for campaign 7 using `traffic-text-v2-sourced`:
Arabic package 15 and English package 16 share generation UUID
`d38887e2-7ed3-48c5-b2cd-f163ed126f02`, remain drafts, and record `who-seat-belts`.
GET `/contents/15` returned 200 with matching content and references. The attached
GET `/campaigns/7/contents` response returned 200 and included new drafts 15/16
alongside approved earlier packages 9/10 with their original v1 prompt metadata.
This verifies the new live generation path, reference persistence, and preserved
generation history through the running server.

Initial quality findings: the supplied seat-belt summary supports a possible
reduction in death risk. The generated awareness messages add serious-injury
claims, and English adds the qualifier `significantly`, which are not established
by that supplied summary. Remove those additions or explicitly curate appropriate
support before approval. The English call to action targets drivers; change
`before you drive` to `before every trip` to include passengers. This is a draft
review finding, not a claim that the additional injury statement is globally false.
No stored content was edited or approved as part of recording these findings.

## Phase 3 pilot evaluation completed

Created `evaluation/cases.json` and `scripts/evaluate_text_generation.py` for
repeatable seat-belt, speeding, and distracted-driving evaluation. Live mode makes
three sequential Gemini requests, records outputs/status/latency, checks source
and retrieval consistency, and rolls back temporary database records. Fake mode
is available for process checks and must not be treated as model-quality evidence.

The live run returned 201 for all three cases and produced six draft packages.
Observed request durations: 86.34, 44.66, and 19.64 seconds. Source snapshots,
shared bilingual generation IDs, and PostgreSQL retrieval passed; evaluation
rows were rolled back and existing row counts were unchanged.

Codex-assisted qualitative review found unsupported claim extensions, a mixed
Arabic/Latin typo, and an audience mismatch. No case was ready for approval
without editing. Proposed Arabic/English corrections are saved separately from
the unchanged raw evidence, and all six proposed PATCH bodies pass API schema
validation. This is a small prototype evaluation, not independent human review
or a production reliability/factual-accuracy guarantee. Costs were not measured.

Artifacts:

- `PHASE_3_EVALUATION.md`: rubric, measured outcomes, limitations, and next work.
- `evaluation/runs/20261013T181946294622Z.json`: unchanged raw live capture.
- `evaluation/review_20261013.json`: review findings and proposed corrections.

The regression suite now passes **165 tests**, including six new checks that reject
inconsistent evaluation evidence. Existing generation/edit/review/CRUD behavior
continues passing. Phase 3's planned backend and pilot report are complete for
the graduation-project prototype. Next phase: frontend campaign management,
generation/history views, source display, editing, and explicit human review.
