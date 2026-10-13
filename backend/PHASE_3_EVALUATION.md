# GovReach AI — Phase 3 pilot evaluation

Evaluation date: 2026-10-13 (Africa/Cairo). The raw run identifier uses UTC.

## Result

The three live bilingual generation requests succeeded, giving six structurally
valid drafts with the expected topic references. Storage and retrieval checks
passed for all three topics. The qualitative review found edits needed before
approval in all three cases. A successful API response is not a quality approval.

This completes a small prototype evaluation of the Phase 3 backend and its
human-review workflow. It does not establish automatic factual accuracy,
institutional approval, production reliability, or publication readiness.

## Reproducible setup and evidence

- Model: `gemini-3.5-flash-lite`, low thinking effort.
- Prompt: `traffic-text-v2-sourced`.
- Source catalogue: `traffic-sources-v1`.
- Inputs: [evaluation/cases.json](evaluation/cases.json).
- Raw outputs: [evaluation/runs/20261013T181946294622Z.json](evaluation/runs/20261013T181946294622Z.json).
- Findings and proposed PATCH bodies: [evaluation/review_20261013.json](evaluation/review_20261013.json).
- Regression suite: **165 passed**; automated tests use fake providers.

The live capture used FastAPI's in-process HTTP client, PostgreSQL, and one
sequential Gemini request per topic, without retries. It checked bilingual
structure, shared generation IDs, draft status, expected source IDs, and equality
of saved/retrieved responses. Temporary rows were rolled back; existing campaign
and content counts were unchanged. Sequence values may advance. Captured content
IDs are therefore evidence identifiers, not persistent IDs usable in Swagger.

Repeat from `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m scripts.evaluate_text_generation --live
```

The second command makes three paid/free-tier-quota requests according to the
project's billing tier. It saves a new timestamped capture without overwriting
earlier evidence. Run without `--live` to test the capture with a fake provider;
fake outputs must not be used as model-quality evidence.

## Technical results

| Topic | Generation | Bilingual/source/retrieval checks | Request duration |
| --- | --- | --- | --- |
| Seat belts | 201 | Passed | 86.34 seconds |
| Speeding | 201 | Passed | 44.66 seconds |
| Distracted driving | 201 | Passed | 19.64 seconds |

Observed mean: **50.21 seconds**; median: **44.66 seconds**. These durations include
API/service/database work; they are not pure provider inference measurements.
There was one attempt per topic, so the results do not estimate production
availability or tail latency. Previous development requests returned 503/504,
and this run's slowest request was close to the configured 90-second timeout.
Token usage and monetary cost were not measured by this capture.

## Qualitative review

Review method: Codex-assisted assessment of the raw output against the exact
source summaries supplied in that request. This was not a blind experiment or
an independent Arabic/English human panel. Findings are editorial judgments
for project review, not certification of traffic-safety claims.

Rubric: language/dialect, spelling/readability, bilingual alignment, support from
the supplied facts, audience-appropriate call to action, and draft/review behavior.
An unsupported claim, corrupted word, or audience mismatch requires editing;
structure alone cannot satisfy this rubric.

| Topic | Language and spelling | Factual support | Call to action | Decision |
| --- | --- | --- | --- | --- |
| Seat belts | Readable; recognizable Egyptian Arabic | Adds injury benefits absent from the supplied summary | English excludes passengers | Needs edits |
| Speeding | Arabic contains a mixed-letter typo; English readable | Adds reaction/control benefits absent from the supplied summary | Matches driver audience | Needs edits |
| Distracted driving | Readable; minor Arabic wording improvement | English overstates certainty/degree | Matches driver audience | Minor edits |

For this review, **0/3 cases were ready for approval without edits**. This does not
mean all wording is false; it means the drafts exceed the narrow supplied evidence
or need editorial correction. Proposed corrections are saved in the review JSON,
separately from the unchanged raw capture.

## Review workflow acceptance

Existing API tests and the PostgreSQL diagnostic verify partial editing, separate
approval/rejection, rollback after failures, and reset to `draft` after re-editing.
The user also confirmed generation, retrieval, source references, editing, and
approval in Swagger using persistent campaign 7 content. No evaluation drafts
were automatically approved or published.

To reproduce a topic through Swagger, create a campaign using a case's input,
generate its drafts, inspect the text/references, PATCH only necessary text
fields, retrieve the edited result, and then approve each language separately.
Use the new persistent IDs returned by your own request, not IDs in the capture.

## Scope conclusion and next work

Phase 3's planned backend functionality is implemented and exercised: API-based
Egyptian Arabic/English generation, versioned prompts, curated source context,
atomic persistence, history/retrieval, editing, and review. The pilot evaluation
and limitations are documented. It is suitable to move to Phase 4's frontend
prototype with mandatory draft review clearly represented in the user interface.

Quality hardening remains necessary for broader deployment: improve prompt rules
using these observed failures; expand carefully reviewed source coverage; evaluate
more campaigns and repeated runs; involve independent Egyptian Arabic/English
reviewers; capture token/cost metrics; and address provider latency. Introducing
automatic semantic verification or changing to background generation should be
a separately reviewed design decision, not an untested claim of this pilot.
