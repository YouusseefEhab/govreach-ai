# Phase 4 — GovReach AI frontend plan

## Goal and current baseline

Users should be able to create a campaign, generate Egyptian Arabic/English
drafts, inspect their sources and history, edit them, and approve/reject each
language through the application rather than Swagger.

Inspected on 2026-10-13. Existing frontend:

- React + TypeScript + Vite, with dependencies and lockfile already present.
- A welcome page and a functioning `/health` request.
- A campaign button that currently displays a placeholder alert.
- Installed React Router, TanStack Query, React Hook Form, and Zod.
- Existing CSS and a basic blue/neutral visual foundation.

Verification: `npm run build` passed; `npm run lint -- src` passed. The unscoped
lint command scanned dependencies; scope it to application source during setup.
These checks do not verify the future campaign UI or a live browser workflow.

Continue the existing framework and backend design. This plan does not implement
frontend screens or change backend endpoints. Major architectural changes remain
subject to user confirmation.

## Scope

Build a responsive text-campaign workspace, including bilingual interface labels,
independent content-language direction, source inspection, and human review.
Interface language is separate from campaign language: changing the UI language
must not change which language the campaign generates. The user selected Arabic
as the default interface on 2026-10-21; an English toggle will follow in a later
increment. Generated Arabic stays Egyptian Arabic.

Images, video generation, public publishing, authentication/roles, reviewer audit
trails, background jobs, and cloud rollout follow as separate increments. Do not
show working image/video/publishing controls before those capabilities exist.
Approval remains a review label, not publication or institutional certification.

## User journey

Campaign list -> Create campaign -> Campaign workspace -> Generate draft ->
Inspect text and sources -> Save corrections -> Review each language -> Approve
or reject -> Revisit generation history.

Keep campaign status distinct from content review status. Approving a package
does not mark its campaign or the other language package approved.

## Implementation sequence

### Progress — 2026-10-21

Step 1 implemented: Arabic-default RTL layout (user preference), navigation,
TanStack Query provider, shared configurable API client, campaign/content types,
safe HTTP/network/validation errors, response-shape validation, and backend health.
The first part of Step 2 adds a read-only campaign list with URL pagination,
loading/error/empty states, and isolated Arabic/English titles. The next increment
adds campaign creation with React Hook Form/Zod, explicit saving, pending guards,
retained values on errors, and a details route that can reload the saved brief.
List titles link to details; successful creation invalidates the campaign list.
Campaign editing and confirmed deletion are now implemented. Create/edit share a
form; edit prefills the saved brief and PATCHes only changed fields. Domain and
generated history stay unchanged. Deletion explains the cascade, requires a second
explicit action, disables confirmation controls while pending, and refreshes the
list after success. Step 3 now adds explicit audience/tone generation, a 120-second
browser wait, no mutation retries, pending guards within the app session, and
saved-history checks before resubmitting after errors. Unsupported campaigns show
an explanation instead of allowing generation. The initial Step 4 display adds
paginated five-field cards with independent RTL/LTR, review status, sources, and
generation metadata. Cards are individual content records rather than assumed
complete bilingual groups. Step 5 now adds a per-package editor with partial saves,
saved-preview/source context, confirmed draft reset, and separate approval/rejection.
Dirty/pending forms block review, failures preserve edits, and successful mutations
refresh the affected content/history caches. React Router uses its data-router
provider to support its built-in unsaved navigation blocker; reload/close uses the
native beforeunload warning. Copying, more history detail, browser verification,
and an English UI switch remain pending. Existing backend contracts and database
schema are unchanged. Full reloads/multiple tabs have no shared pending guard;
backend idempotency and cancellation remain outside the current API.

Verification: production build and lint passed; 38 frontend tests passed. The 165
backend tests passed during the preceding campaign-management increment. API client tests
mock fetch and cover pagination, malformed data, validation, HTTP failures,
cancellation, no automatic replay, and empty 204 responses. Server-rendered route
tests cover Arabic navigation, mixed-language titles, pagination controls, empty
lists, and missing pages. They do not replace browser interaction/visual checks.
The browser-control runtime failed to initialize, so visual, keyboard interaction,
and mobile viewport checks remain pending.
Local HTTP checks returned 200 for `/` and `/campaigns`; FastAPI `/health` and
the campaign-list endpoint returned 200 with the correct localhost:5173 CORS
origin. The initial list read two existing campaigns. Creation was then checked
with the real frontend API client: create a disposable campaign, retrieve it twice,
find it in the list, and delete only that test campaign. Existing campaigns were
preserved; no Gemini requests were made. The user confirmed campaign creation in
the browser. A further disposable campaign check verified title-only editing,
language editing, preservation of other fields, deletion, final 404, and absence
from the list. Browser edit/cancel-delete/confirm-delete, focus, and pending-state
walkthroughs remain pending. Automated render tests cover edit defaults and the
confirmation warning/disabled controls; they do not simulate clicks.
Generation checks mock audience validation, 201 response decoding, 502/503/504,
network loss, browser timeout, no automatic POST replay, and GET-only paginated
history. Render checks cover pending/recovery-disabled forms and safe directional
content/source display. Existing histories were fetched through the real frontend
client (read-only). The PostgreSQL fake-provider diagnostic passed generation 201,
retrieval/edit/review 200, and cascade deletion 204/404; all diagnostic writes rolled
back. No live Gemini call was made. Browser generation clicks, navigation during
pending, and visual layouts remain unverified by automation because its runtime
could not initialize.
Editor tests cover all field limits, partial PATCHes, separate edit/review requests,
draft-reset response checks, failed reviews without retries, dirty/pending disabled
controls, and a data-router editor reload render. Live GETs retrieved existing
content records; no user packages were edited. The fake-provider PostgreSQL
diagnostic again verified edit/review/reset behavior and rolled back all writes.
Actual form clicks, navigation-blocker interaction, and close/reload prompts still
need browser checks. Build emits a non-blocking >500 kB chunk advisory; splitting
is deferred to polish rather than changing implementation scope here.
See the frontend README for local setup and verification commands.

| Step | Work | Acceptance result |
| --- | --- | --- |
| 1. Foundation | App layout, routing, shared API client, server-state provider, public API configuration | Navigation works and the UI reaches FastAPI |
| 2. Campaign management | List, create, view, edit, and delete campaigns | CRUD works through the UI and survives refresh |
| 3. Text generation | Audience/tone form, explicit generation action, pending/error states | New drafts are saved and displayed without duplicate automatic calls |
| 4. Content and history | Language packages, generation history, sources, metadata | Saved packages and reference snapshots are accessible after reload |
| 5. Editing and review | Field-level edits, save, approve/reject, draft-reset feedback | Edited packages return to draft; review is a separate action |
| 6. Arabic and responsive polish | UI translations, RTL/LTR, keyboard/focus behavior, small-screen layouts | Arabic/English content remains readable across screen sizes |
| 7. Verification and demo | Focused workflow tests, build/lint, browser checks, demo guide | A reproducible frontend-to-PostgreSQL demonstration passes |

Implement and verify one step at a time, explaining changes before proceeding.

### Step 1 — foundation

- Preserve the welcome/health functionality while replacing the placeholder action.
- Use React Router for navigation and TanStack Query for API reads/mutations.
- Extend the existing `src/services/api.ts` instead of creating competing clients.
- Add TypeScript types matching campaign and persisted-content API responses.
- Configure `VITE_API_BASE_URL` in a frontend `.env.example`. This is a public URL;
  Gemini keys, database credentials, and backend secrets remain server-side.
- Standardize on `http://localhost:5173` during local development, matching existing
  CORS. If `127.0.0.1` or another port is needed, explicitly align the backend
  allowed origin rather than adding an unrestricted wildcard.
- Handle JSON errors, FastAPI 422 field errors, network failures, and missing data
  centrally. Show useful user messages without stack traces or credentials.
- Scope lint to `src` and relevant project configuration files, excluding dependencies.

Vite exposes `VITE_*` values to the browser; see [official environment guidance](https://vite.dev/guide/env-and-mode).
Generation and save actions should be mutations with retries explicitly disabled;
see [TanStack mutation guidance](https://tanstack.com/query/latest/docs/framework/react/guides/mutations).

### Step 2 — campaign management

Campaign list shows title, domain, language, status, and creation date. Support
empty/loading/error states and Previous/Next pagination using `skip`/`limit`.
The API does not provide total counts, so do not invent totals or page counts.
Global search/filtering and aggregate dashboard statistics need API support and
are optional follow-up work.

Creation collects title, objective, and Arabic/English/both selection, with
`traffic_safety` as the initial generation domain. Campaign CRUD currently accepts
other domains, but generation rejects them; explain this before generation.
Mirror existing backend constraints rather than silently changing them.

Campaign editing preserves generated history. The workspace should explain that
editing the brief does not rewrite old packages; users generate again when ready.
Deletion needs a clear confirmation that all generated content/history for that
campaign will also be deleted. Use a disposable campaign for deletion tests.

### Step 3 — generation

- Require audience, allow informative/encouraging/formal tone, and show the campaign's
  stored content language. Use the existing POST generate-text contract.
- Generate only when the user explicitly submits. Never generate on mount,
  navigation, language toggles, background refresh, or query retries.
- Disable duplicate submission while pending. Show honest waiting feedback without
  invented percentages; observed generation durations reached about 86 seconds.
- Keep the client request timeout longer than the backend's 90-second provider
  timeout, allowing time for validation/storage and a controlled error response.
- Handle 502 (unusable output), 503 (provider/storage unavailable), and 504 (timeout).
  Preserve the form and existing drafts on error.
- A lost browser connection does not prove that server generation was cancelled.
  Refresh saved history before deciding to submit again; there is no idempotency
  key or cancellation endpoint yet.
- Repeated successful submissions intentionally create new history and consume
  another provider request. Keep that behavior clear in the workflow.

### Step 4 — content, history, and sources

Present headline, slogan, awareness message, caption, and call to action in clearly
labelled Arabic/English packages. Use RTL for Arabic content and LTR for English
regardless of interface language. Stack packages on narrow screens.

Show review status and generation date, with source details available beside the
text. Display publisher, title, relevant section, and a usable HTTPS link. Explain
that references were supplied to generation; they are not automatic fact-checking
or government endorsement. Older packages may have no references, and human edits
retain their original source snapshots.

History preserves earlier generations and uses stored generation UUIDs to identify
paired language variants. Pagination is by content records; account for a pair
split across pages before presenting a generation as complete. Provider/model and
prompt version can be available under expandable generation details.

Treat generated text as plain text. Do not render it as raw HTML or executable
markup. Copy buttons copy the selected text accurately, including Arabic.

### Step 5 — editing and review

Allow edits to individual text fields with the existing character limits and
required nonempty values. Send only changed fields inside `content`. Preserve
unsaved edits after validation or network errors and prevent accidental loss when
navigating away.

Saving changes resets the selected package to draft. Keep save and approve/reject
actions separate, and disable review actions while edits are unsaved. After save,
show the server response before offering approval. Avoid optimistic approval labels
that imply a failed request succeeded.

Source inspection and wording checks are part of review. Approve/reject Arabic and
English independently. Approval does not publish, approve other packages, or
certify factual correctness. This phase must not invent reviewer identity/time or
an edit audit trail that the backend does not store.

### Step 6 — language, accessibility, and responsiveness

- Translate navigation, labels, validations, and status/error messages through a
  shared message catalogue rather than embedding duplicate strings in each page.
- Keep Arabic URLs, IDs, timestamps, and English snippets readable within RTL layouts.
- Use visible labels, keyboard-operable controls, meaningful focus after actions,
  and status indicators that do not rely solely on colour.
- Verify Arabic punctuation, long objectives, source links, five-field editors,
  and language switching at desktop and mobile widths.
- Persist interface-language preference without changing campaign content language.

## Planned screens and organisation

| Route | Screen |
| --- | --- |
| `/` | Welcome/start page with working campaign navigation |
| `/campaigns` | Campaign list |
| `/campaigns/new` | Create campaign |
| `/campaigns/:campaignId` | Campaign workspace, generation form, and history |
| `/campaigns/:campaignId/edit` | Edit campaign brief |
| `/contents/:contentId` | Text editor, source inspection, and review |

Extend the existing `pages`, `services`, and CSS structure. Add reusable layout,
campaign form, content card/editor, status, and source components as needed.
Keep shared types, query hooks, and UI-language messages in small dedicated
modules. Do not introduce a separate state framework or backend redesign without
a concrete need and confirmation.

## API mapping

| UI action | Existing API |
| --- | --- |
| Health | GET `/health` |
| List/create campaigns | GET/POST `/api/v1/campaigns` |
| View/edit/delete campaign | GET/PATCH/DELETE `/api/v1/campaigns/{id}` |
| Generate new text | POST `/api/v1/campaigns/{id}/generate-text` |
| Read history | GET `/api/v1/campaigns/{id}/contents` |
| Read/edit/review package | GET/PATCH `/api/v1/contents/{id}` |

Invalidate/refetch only the affected campaign/content queries after successful
mutations. Reading history must never trigger regeneration. No new generation
database schema is required for this plan.

## Phase 4 acceptance and test plan

Use mocked API responses for repeatable frontend failure/interaction checks.
Focus tests on duplicate-generation prevention, dirty edits blocking approval,
draft reset after save, server-error field mapping, and RTL/language separation.
Do not incur Gemini charges in automated frontend tests.

Browser walkthrough against FastAPI/PostgreSQL:

1. Create and edit a disposable bilingual traffic-safety campaign.
2. Generate once; inspect five-field Arabic/English drafts and references.
3. Reload the page and retrieve the saved generation.
4. Correct a field, save it, and confirm other fields/packages remain unchanged.
5. Approve/reject each language separately; re-edit and confirm draft reset.
6. Check history, pagination, copy controls, and language switching.
7. Exercise mocked 422/502/503/504, offline, empty, and missing-record states.
8. Confirm deletion cascades only for the disposable campaign.
9. Pass production build, source lint, and the existing backend regression suite.

Phase 4 is complete when this flow works through the interface, including errors,
refresh/navigation, Arabic presentation, sources, and review. Keep a demo guide
and record which checks were mocked, live, or manual. Publishing, cloud access
controls, images, and video remain future scope.

First implementation increment after this plan: layout/navigation and API-client
foundation, followed by campaign listing and creation. Review visual/interface
preferences before committing to a substantial redesign.
