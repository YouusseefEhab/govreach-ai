# Phase 5 proposal: reviewed campaign images

Prepared 2026-10-21. **Foundation approved and implemented; paid usage remains unapproved.**

## Updated provider decision — Cloudflare Free first

The user chose Cloudflare Workers AI with FLUX.1 Schnell for images until a later
paid-API decision. Gemini remains the text provider. The earlier Gemini image
comparison below is retained as a future alternative, not the current default.

Implemented a fixed-model Cloudflare adapter and backend configuration; default
is still fake until account credentials and explicit Free-plan confirmation are
provided. No paid fallback, billing API calls, automatic retry, redirects, or live
model selection. HTTP/base64 response sizes are bounded and raw error bodies are
not exposed. The existing image reservation stores actual provider/model/prompt
version when Cloudflare is used; same-key replay still returns the original row.

Verification: 244 backend tests pass, including mocked Cloudflare success, quota,
credentials/access, timeout/transport ambiguity, malformed output, prompt/size
limits, redirects, provider provenance and one-call replay. External HTTP and
Gemini clients are blocked by the test fixture. No real Cloudflare account or
image request was accessed during implementation. No migration was needed.

Follow [Cloudflare setup](CLOUDFLARE_SETUP.md). The Free-plan flag is user confirmation,
not an automatic billing-subscription check. Keep the account on Free; quota
exhaustion stops requests. The fake diagnostic remains the default; an explicit
`--cloudflare` option performs one quota-consuming test after configuration.
Endpoints, cleanup/recovery and UI remain next. Paid APIs still require a budget.

## Current progress — validation and fake pipeline

Implemented the second increment on 2026-10-21:

- Pinned Pillow 13.0.0 in runtime requirements/constraints. Verification opens,
  checks and fully decodes PNG/JPEG data, checks claimed MIME against detected
  format, rejects corrupt/truncated/non-square/animated output, and enforces byte,
  edge and pixel limits before full pixel loading. Original bytes are retained.
  See [Pillow image verification](https://pillow.readthedocs.io/en/stable/reference/Image.html).
- Added an image-provider protocol, safe provider error boundary and deterministic
  fake provider. Its blue 32×32 PNG is a test placeholder, not AI campaign artwork.
- A fake-only service reserves/claims the request, releases its database transaction
  before the provider call, validates output and rechecks/locks the source before
  saving verified file metadata as a ready **draft**. No image is auto-approved.
- Same-key replays return saved state without invoking the provider again. Policy
  refusal/invalid output/storage failure are distinguished from ambiguous timeout/
  transport outcomes. Unexpected provider error bodies are not exposed.
- Database/storage are not atomic: proven orphan files are cleaned up after failed
  persistence. A lost commit acknowledgement is checked against saved metadata;
  potentially referenced bytes are retained when database state cannot be read.
  Cleanup failures are logged for later reconciliation. The reconciliation command
  and cascade/file integration remain prerequisites for public endpoints.
- Added `scripts.check_image_pipeline` and a fake-only PostgreSQL CI check.
  The diagnostic creates temporary files and rolls back its temporary rows.

Verification: 219 backend tests pass; dependency check passes; PostgreSQL fake
pipeline diagnostic passes (verified image, file reload, idempotent replay and stale
source detection). Alembic reports no schema drift; no new migration was needed.
Existing campaigns/text are untouched. No paid generation, real image adapter,
image endpoints or image frontend are enabled. Keyboard testing remains deferred.

Run the safe diagnostic from `backend`:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt -c constraints.txt
.venv/Scripts/python.exe -m scripts.check_image_pipeline
```

It has no live mode and creates no lasting demo image. The next increment is the
image API plus cleanup/recovery integration; real-provider access and paid pilot
still require an agreed budget.

## Progress — first implementation increment

The user approved the proposed text-free square-image foundation, separate image
table, local storage, and separate Gemini image adapter. This increment implements
only persistence/storage and provider-free reservation rules. The real adapter,
image decoding, generation/file/review API routes and image UI follow later.

- Added `image_generations` through Alembic revision `c9e51a70d682` (after
  `b7f23e8d10a4`). Existing text schema/constraints are unchanged.
- Persisted campaign-scoped request identity/hash, source snapshots/hash/references,
  draft review status and request lifecycle. Same-key replay returns the original
  row; conflicting inputs are rejected. A conditional update claims a reserved
  request once; interrupted outcomes cannot be automatically reclaimed.
- Reservation accepts approved traffic-safety text belonging to the campaign.
  Source eligibility detects subsequent text edits or loss of approval.
- Added local storage behind a protocol: generated keys, PNG/JPEG byte containers,
  bounded writes/reads, checksum, traversal/symlink rejection and idempotent deletion.
  Storage is intentionally an opaque-byte boundary, **not an image decoder**.
  Actual pixel/MIME/dimension verification is required before exposing an API or
  marking an artifact ready in the upcoming pipeline.
- Media defaults to ignored `data/media`; no directory is created at import.
  Added `MEDIA_MAX_BYTES` example configuration and a repository media-file guard.
  No production image files were created. Cascade/file reconciliation is still
  pending and must be integrated before ready images can be generated/deleted.
- Provider/model are explicitly fake in reservations for this increment. There is
  no live image implementation or paid image request path yet.

Verification: all 191 backend tests pass (26 new tests), including disposable
migration upgrade/downgrade, preserved text rows, identity/state constraints,
snapshots, source eligibility, cascade isolation and temporary fake PNG storage.
The PostgreSQL migration was applied; Alembic reports no drift. Before/after hashes
confirmed preservation of 3 existing campaigns and 8 text packages. The existing
fake-provider PostgreSQL text API diagnostic also passed and rolled back its rows.
No real Gemini calls or billing changes were made. No new frontend behavior in
this increment. Keyboard testing remains deferred.

## Goal and scope

Extend the existing text workflow so a user can select an approved traffic-safety
text package, prepare an image brief, generate one image, retrieve it after reload,
review it independently, and download it. Preserve the working text pipeline.

Phase 4's core workflow and mobile checks are user-confirmed; keyboard testing is
deferred. This proposal does not close that verification item.

The separate, untracked `docs/GRADUATION_1_PLAN.md` recommends excluding media from
the Graduation 1 MVP. It is a draft scope recommendation, not a new instruction
or proof of supervisor approval. Phase 5 is an optional extension to confirm
against academic priorities; the draft and university source files remain unchanged.

First release: text-free, square, approximately 1K traffic-safety artwork, with one
image per explicit request. Illustrations should support the selected message and
Egyptian context. Generated artwork starts as draft and requires visual review.
The same text-free artwork can accompany either language; it is not a translation.

Later: deterministic Arabic/English poster text overlays, additional aspect ratios,
image-to-image editing, uploads, batch jobs, and video. Generated Arabic typography
is not an acceptance dependency for the first release. No public publishing or
government endorsement is implied by image approval.

## Inspected baseline

- Python/FastAPI, SQLAlchemy/PostgreSQL, Alembic, Pydantic, React/TypeScript.
- Existing Gemini SDK and a separate text-provider interface.
- `generated_contents` is constrained to `text_package` and Arabic/English records;
  images must not be inserted there by relaxing its checks.
- Text packages already have source snapshots, generation IDs, edit-to-draft
  behavior and independent review status.
- No image provider, image model setting, media storage, image table, or image API
  exists yet. Redis configuration alone does not establish a worker system.
- The prototype has no authentication. Keep media work local/controlled; public
  cloud exposure needs a separate access-control/deployment decision.

## Proposed user journey

Campaign → select approved text package → review/edit visual brief → generate once
→ preview draft image with its originating brief → approve/reject image → download.

1. The user chooses a saved package, not an unsaved editor buffer.
2. The server verifies campaign membership, traffic-safety domain and approved text.
3. A versioned template builds a proposed brief from that package and its audience.
   No extra LLM request is required just to prepare the first brief.
4. The user reviews subject, scene, style and exclusions before generation.
5. The server snapshots the selected text, prompt, sources and settings, calls the
   image provider once, validates actual image bytes, stores them, and returns metadata.
6. The UI displays saved images/history, honest pending/errors and independent
   review controls. Reads, language switching and refresh never generate an image.
7. Each new generation creates a new artifact; earlier images stay available.

Example: approved seat-belt message → parked car, driver/passengers correctly
wearing belts, recognisable everyday Egyptian setting, no written slogans, no
official seals/logos, no invented statistics. A reviewer checks belt placement and
scene correctness rather than treating a plausible illustration as validated advice.

## Provider options and cost

Recommend Google's existing SDK/account family for the first integration, through
a **new image-provider adapter**, leaving the text adapter/settings unchanged.
Reusing an SDK does not mean the configured text model can generate images.

Candidate models to verify against the user's API project before selection:

| Candidate | Role in the pilot |
| --- | --- |
| `gemini-3.1-flash-lite-image` | Proposed first 1K, single-image candidate |
| `gemini-nano-banana-2.1` | Comparison candidate if quality justifies it |

Google currently documents both families. Account access, exact SDK call/response
shape and availability must be verified during the capability check; do not lock
an implementation to a name copied from an older tutorial. The current Imagen
guide says Imagen is shut down, so it is not a new-integration candidate.
[Image guide](https://ai.google.dev/gemini-api/docs/image-generation),
[Imagen status](https://ai.google.dev/gemini-api/docs/imagen).

The current pricing page lists $0.0336 per 1K image output for each candidate,
plus applicable input/text/thinking charges; neither has a free-tier API entry.
Six outputs would be approximately $0.2016 in image-output charges alone, not a
complete quote. Recheck prices before live tests.
[Official pricing](https://ai.google.dev/gemini-api/docs/pricing).

API-project billing must be checked separately; a consumer Gemini subscription
is not evidence that this API project has image access or credits. Do not enable
billing, buy credits, or change account limits while implementing this plan.
[API billing](https://ai.google.dev/gemini-api/docs/billing).

Proposed pilot: at most six deliberate live calls across three topics and two
candidates, with an agreed total allowance (suggestion: USD 2, **not yet approved**).
Record latency, returned usage when available, model/settings, file size and review
result. Estimated app usage is not an invoice or an account-wide hard spending cap.
Use one output/request, no automatic paid retries, explicit generation and an app
request-count ceiling. Mock providers remain the default in tests and CI.
Unexpected multiple-image responses must be handled explicitly; one app request
is not a guarantee of one billed output. Record actual returned usage when supplied.

## Architecture decisions to confirm

| Decision | Proposed first implementation | Reason / limit |
| --- | --- | --- |
| Image data | New `image_generations` table via a new Alembic revision | Preserve existing text constraints and history |
| Binary storage | Ignored local media directory behind a storage interface | Simple local prototype; cloud uses persistent object storage later |
| Provider | Separate Gemini image adapter and image-specific configuration | Independent capability, timeout and error handling |
| Execution | One bounded synchronous provider call per request | Reuse current request style without adding a queue immediately |
| Request identity | Persisted idempotency key and request state | Do not rely only on a disabled browser button for a paid action |
| Review | Independent draft/approved/rejected image status | Text approval must not approve image output |

If measured image latency regularly exceeds the acceptable request window or
target cloud proxy limits, stop at the pilot checkpoint and propose persistent
background jobs. Do not quietly introduce Celery, a worker deployment or another
framework. A synchronous first version is a deliberate prototype tradeoff.

Cloud preparation means storing a storage key, not a local absolute path or an
expiring signed URL in the database. No cloud bucket/provider is selected or
provisioned by this plan. Local files are not durable on an ephemeral cloud disk.

## Proposed persistence and consistency rules

One `image_generations` record can track the request and its eventual artifact:

- ID; campaign ID; source-content ID; timestamps.
- Scoped unique idempotency key; canonical request hash.
- Request state: reserved, generating, ready, failed, or outcome_unknown.
- Source-text snapshot/hash, supplied-source snapshots, final visual brief,
  prompt-template version, provider/model and generation settings.
- Optional storage key, verified MIME type, width/height, byte count and checksum
  once ready; safe failure code otherwise.
- Image review status, initially draft when ready. No fabricated reviewer identity
  or review timestamp beyond what is explicitly implemented.

Exact field names/check constraints are reviewed before the migration is written.
The same idempotency key with the same body returns the existing result/state;
the same key with a different body returns conflict. Never repeat the provider
call for a request that may have reached it. Timeout/restart ambiguities become
outcome_unknown for inspection, not an automatic retry. This cannot guarantee
provider-side exactly-once execution if the provider offers no idempotency support.

Reserve/commit request identity before the network call, then release the database
transaction/locks while waiting. Revalidate the source snapshot/status before
making the artifact eligible for approval. If approved text later changes or loses
approval, retain the image's original snapshot and show it as stale/ineligible for
current use. Do not silently rewrite its provenance or imply old approval covers
the changed brief. Review and eligibility remain distinct concepts.

Store image bytes outside PostgreSQL. Validate content, MIME, dimensions, byte
limits and checksums; accept a small explicit raster allowlist (initially PNG/JPEG),
not active SVG/HTML. Use generated filenames/keys and bounded decoding. Keep raw
provider bodies, keys, temporary files and image binaries out of Git and logs.

File writes and database commits are not one transaction. Stage/validate the file,
finalise metadata, and perform compensating cleanup on failure. Campaign deletion
must collect associated keys, preserve the existing DB cascade, and remove media
after commit. Failed cleanup needs a logged, retryable reconciliation command,
with dry-run and protection for in-flight/young files. Test missing files/orphans
and document any prototype cleanup limits instead of promising atomic deletion.

## Proposed API contract

These routes are proposals, not existing endpoints:

| Method / route | Purpose |
| --- | --- |
| `POST /api/v1/campaigns/{id}/generate-image` | Source content ID, reviewed brief/style, fixed initial format; required idempotency key |
| `GET /api/v1/campaigns/{id}/images?skip=0&limit=20` | Persisted image request/history records |
| `GET /api/v1/images/{id}` | Metadata, request state, review status and source eligibility |
| `GET /api/v1/images/{id}/file` | Validated file preview/download for ready records |
| `PATCH /api/v1/images/{id}` | Separate review of a ready image; approval requires current source eligibility |

First successful generation returns 201. Idempotent replay of a ready record
returns its existing result; pending/unknown states return inspectable metadata,
not another generation. Specify final replay/status semantics in schemas before
coding. Use 404 for missing/mismatched campaign/source, 422 for invalid fields,
409 for non-approved/stale source or conflicting request identity, and safe
502/503/504 provider/storage/timeout responses. Provider policy blocks get a
distinct safe reason; they are not described as malformed image bytes.

File routes resolve DB keys under the configured storage root, never arbitrary
client paths. Return correct image content types and controlled download names.
Document that local prototype routes are not authenticated or public hosting.

## Implementation sequence

| Step | Deliverable | Completion check |
| --- | --- | --- |
| 1. Confirm scope and capability | Architecture choices, project access, model candidate and live-call allowance | Explicit user decisions; no surprise billing changes |
| 2. Storage and persistence | New migration/models, storage interface/local adapter, idempotency states and cleanup design | Existing data intact; reversible isolated migration tests; no AI calls |
| 3. Image provider and validation | Fake adapter first, real Gemini adapter second, fixed prompt template and safe errors | Fake output saves and reloads; invalid/blocked/oversized output rejected |
| 4. Backend API | Generation/history/file/review routes and source eligibility | API tests cover success, replay, failures and cleanup |
| 5. Bilingual frontend | Approved-package selection, brief, explicit generate, preview/history/review/download | Refresh preserves images; Arabic/English UI works without duplicate calls |
| 6. Small live pilot and sign-off | Bounded image samples, review findings and demo guide | Visual quality/cost/latency measured; limitations recorded |

Explain and verify each increment before proceeding. Commit meaningful checked
increments; preserve the existing text tests and API behavior. The first coding
increment after approval is fake storage/persistence, not a paid image request.

## Test and evaluation plan

Automated: fake image provider; temporary files/database; no paid CI calls. Cover
approved-source gate, wrong campaign, partial/malformed images, policy block,
timeout, quota/unavailable errors, duplicate/in-flight keys, restart ambiguity,
storage/DB failures, cleanup/cascade, stale source, review decisions and download
content type. Confirm existing text generation/edit/review still works.

Frontend: explicit-submit-only, pending duplicate prevention, error retention,
history recovery, stale-source labels, separate review, correct image alt text,
download, both UI directions, mobile and keyboard controls. Do not invent a
generation percentage or render a failed image as an empty successful result.

Pilot topics: seat belts, speeding and phone distraction. Review each image for
message relevance, road-safety correctness, Egyptian context, unsafe/misleading
details, visual defects and accidental text/logos. Include a human reviewer;
record who actually reviewed, the rubric, corrections/rejections, latency and
usage evidence. A small pilot is not a reliability benchmark or official approval.

Acceptance: one approved text package produces a saved draft image; it survives
reload/server restart with persistent local storage, can be independently reviewed
and downloaded, has traceable snapshots, handles ambiguous outcomes honestly, and
does not regress text functionality. Failed generations do not create ready images.

## Decisions still open

1. Media foundation and the proposed initial architecture are approved. Keep the
   Graduation 1 scope/deadline tradeoff visible rather than claiming university approval.
2. Decoded-image validation and a fake provider pipeline are implemented. Next:
   API routes and cleanup/recovery integration, then the real adapter and UI.
3. Verify image API access and agree a live-call budget before paid testing.
4. Text-free square images are approved as the initial format; overlays remain later.

The original proposal changed documentation only. The progress section records
subsequent implementation and the applied additive database migration. Billing and
real provider configuration remain unchanged. Recheck linked provider documentation
at the capability gate because models and prices can change.
