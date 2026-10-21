# GovReach AI frontend

React + TypeScript + Vite application for the graduation project. The current
implementation contains an Arabic-default bilingual RTL/LTR layout, welcome page, backend health
check, paginated campaign list, shared campaign create/edit form, saved campaign
details, confirmed deletion, text generation, paginated saved text/source cards,
and per-language content editing/approval/rejection. Further interface work is planned in
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

Routes: `/`, `/campaigns` (optional `?page=2`), `/campaigns/new`, and
`/campaigns/:campaignId`, `/campaigns/:campaignId/edit`, and `/contents/:contentId`.
Create collects title, objective, and language, with
traffic safety fixed as the initial domain. It saves once per submission, then
opens the saved details. Errors preserve the form; after a lost connection check
the list before resubmitting. Saving does not generate AI content.
Editing prefills the saved brief and sends only changed title/objective/language
fields. Domain, status, and generated history are preserved. Deletion requires
opening a confirmation and explicitly confirming removal of the selected campaign,
all generated content, and history. Failed deletes keep the confirmation and
display an error; success returns to the refreshed campaign list.
Previous/Next uses the API's `skip`/`limit`;
an exactly full final page can lead to an empty next page because there is no
total count. The health indicator checks process responsiveness, not the database.
The header language selector switches Arabic/English UI and persists the preference
locally. Campaign language and generated text remain independent. Switching does
not remount forms or trigger generation. Known UI validations/errors and feedback
are translated; source titles/sections stay as supplied.
Each content card has exact-text copy buttons for individual fields and the full
five-field package. Clipboard failure shows a manual-copy instruction, not success.

## Text generation

Open a traffic-safety campaign, enter its audience, select a tone, and explicitly
choose **ولّد مسودة جديدة**. Language comes from the campaign. The request waits
up to 120 seconds, longer than the backend's 90-second provider limit. No generation
is triggered by navigation, rendering, refresh, or history reads; mutations are not
automatically retried. The pending request blocks another submission for that
campaign within this app session, including when navigating away and back.

Errors retain the audience/tone and require **راجع المحتوى المحفوظ** before another
submission. Successful history retrieval unlocks the form; inspect the displayed
packages first. A connection failure or browser timeout does not prove generation
was cancelled on the server. Reloading the entire app or opening another tab loses
the in-memory pending guard; there is no backend idempotency/cancellation endpoint.

Saved packages display the five text fields, their own RTL/LTR direction, review
status, sources, and generation details. Each page contains content records, not
complete generation groups; a bilingual pair may span pages. Group UUIDs identify
related records. Source links only accept HTTPS, and text is rendered as plain
text. References were supplied to generation and do not certify the output.

## Content editing and review

Choose **تعديل ومراجعة النسخة** on a saved package. Edit any of its five fields;
only changed fields are PATCHed. Save waits for the server, updates the saved
preview, and resets the selected package to draft. Existing metadata/source
snapshots and other language packages are preserved. Failed saves retain edits.

Approve/reject are separate requests and are disabled while the form is dirty or
a request is pending. Review status changes only after a successful server
response. Approval affects only this package; it does not publish or certify it.
The editor has no reviewer identity/timestamp or per-edit audit log because the
backend does not store those values.

The existing React Router now uses `createBrowserRouter`/`RouterProvider` so its
built-in `useBlocker` can warn before internal navigation with unsaved edits.
`beforeunload` provides the browser's native warning on reload/close. Choosing
to discard allows leaving; pending requests must finish before internal departure.
The native warning can still be overridden by the user/browser.

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
Form tests check blank input, Unicode title limits, and language choices.

Manual walkthrough: choose **حملة جديدة**, submit blank fields to check validation,
then enter a title/objective and choose a language. Save, confirm the success
message and details, reload, and return to the list. The brief and language must
remain saved. Browser interaction checks remain pending because the automation
runtime could not initialize. The user confirmed creation works in the browser.
Next manual checks: edit a disposable campaign, refresh its details, open the delete
confirmation and cancel (campaign must remain), then confirm deletion (it must
disappear). Never use an important campaign for the deletion walkthrough.
Live API verification used the real frontend client to create/read/partially edit/
delete only disposable campaigns, checking preserved fields and a final 404.
No Gemini calls were made. Automated checks: 46 frontend tests, frontend lint/build,
and the PostgreSQL fake-provider API diagnostic passed. The existing backend suite
also passed its 165 tests in the preceding campaign-management increment.
Live GET checks retrieved existing histories through the frontend client.
Focus restoration and click/pending behavior still need browser interaction checks.
The user subsequently confirmed the full core workflow works, including review,
refresh, draft reset, unsaved-edit warnings, and deletion confirmation. See the
[verification record](PHASE_4_VERIFICATION.md) for evidence and the remaining
keyboard checklist. The user also confirmed mobile controls/layout work; device
and viewport specifics were not supplied. Keyboard testing is deferred until later.

Generation walkthrough (a real provider request may consume quota/credits): open a
test traffic-safety campaign, set audience/tone, and generate once. Wait without
resubmitting. Confirm saved packages and sources, reload, and verify the same IDs
remain in history. On an error, check saved content before deciding to submit again.
Routine automated tests use mocked fetch or a fake provider, not Gemini.

Editor walkthrough: open a saved test package, change one field, and confirm review
buttons are disabled. Try leaving and choose **كمّل المراجعة** to keep edits. Save;
check draft status and preserved other fields, approve separately, reload, and check
the saved status. Edit and save again; status must return to draft. Check the other
language package remains unchanged. Try rejecting separately too. These browser
click/navigation checks remain manual; automated tests cover API/schema/markup
behavior. Live GETs confirmed editor retrieval against existing packages without
editing them; the fake-provider diagnostic checked editing/review with rolled-back
test rows. Build currently has a non-blocking advisory about its >500 kB JS chunk;
route splitting can be addressed in the later performance/polish increment.
See the [project README](../README.md) for backend setup and scope.
