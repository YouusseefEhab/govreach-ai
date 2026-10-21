# GovReach AI frontend

React + TypeScript + Vite application for the graduation project. The current
implementation contains an Arabic RTL layout, welcome page, backend health
check, paginated campaign list, shared campaign create/edit form, saved campaign
details, and confirmed deletion. Generation, history, source, and review screens are planned in
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
`/campaigns/:campaignId`, and `/campaigns/:campaignId/edit`.
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
No Gemini calls were made. Automated checks: 23 frontend tests and 165 backend
tests passed, along with frontend lint/build. Focus restoration and click/pending
behavior still need browser interaction checks.
See the [project README](../README.md) for backend setup and scope.
