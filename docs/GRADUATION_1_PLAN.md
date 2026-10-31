# GovReach AI Graduation 1 completion plan

Prepared 17 October 2026. Submission deadline: **8 December 2026**, interpreting
the supplied date 8/12/2026 as day/month/year in the Africa/Cairo timezone.
Scope: Graduation 1 only. Team names, skills, and weekly availability are pending.

The goal is a working, evaluated bilingual traffic-safety campaign prototype and
the complete academic submission package. Reuse the existing backend and pilot
evidence, finish the frontend, and write the thesis alongside implementation.
This is a proposed allocation, not a record of completed work or supervisor approval.

## Source documents and interpretation

Read in full for content:

- `C:/Users/pc/Downloads/GRAD 1 REQUIREMENTS 1.pdf` (37 pages).
- `C:/Users/pc/Downloads/Standard Graduation Project Thesis Table of Contents.docx`.
- `C:/Users/pc/Downloads/General Thesis Notes.docx`.

The PDF supplies the deliverables and phase checkpoints. The table of contents
supplies the detailed six-chapter structure. General notes supply writing,
diagram, citation, formatting, and testing rules. Examples about other projects
illustrate expectations; they are not GovReach features or evidence.

The PDF phase headings specify: Phase 1 week 1, Phase 2 week 3, Phase 3 week 4,
AI dossier weeks 1-4, MVP weeks 5-7, and final package weeks 8-10. Its sample
Gantt uses different example checkpoints. Confirm actual university checkpoint
dates with the supervisor; the compressed dates below are our proposed remaining
work schedule, not a replacement for official deadlines.

Repository development phases use different numbers. Backend Phase 3 completion
does not demonstrate completion of university Phase 3 requirements.

## Current evidence and remaining work

Status reflects repository inspection on 17 October, not a fresh test run.
Items absent from the repository may exist elsewhere with teammates; collect
them before recreating them.

| Required submission | Evidence already available | Remaining work | Lead |
| --- | --- | --- | --- |
| 1. Charter, risk/ethics sheet, Gantt | README defines purpose and scope; security guidance exists | 2-3 page charter, named ownership, measurable MVP criteria, 3-4 initial risks with likelihood/impact/mitigation, ethics sheet, dated Gantt | P1 |
| 2. Phase 1 report | Basic purpose and traffic-safety scope | Evidence-backed motivation, one-paragraph problem, 3-5 objectives, at least two personas, market review, gap, boundaries | P1 |
| 3. Literature and existing solutions survey | Technical and source references in implementation docs | Research synthesis, product review, cited comparison, defensible gaps, gap-to-feature mapping | P1 with P4 |
| 4. Analysis and architecture pack | Layered backend, database models/migrations, high-level README diagram, API contracts | Numbered FR/NFR, formal use cases, module mapping, complete explained diagrams, database design, field sensitivity/access notes, UI designs | P2 with P3/P5 |
| 5. AI design dossier | Gemini adapter, versioned prompts, curated source catalogue, pilot inputs/raw outputs/review findings | Model rationale and alternatives, data/evaluation protocol, expanded experiments, independent review, safety/bias analysis, consolidated Chapter 4 | P4 |
| 6. Methodology and implementation document | Detailed backend phase notes and run instructions | Frontend and integration explanation, reproducible environment, actual deployment/access limitations, Chapter 5 | P2 with P3/P4 |
| 7. Working MVP, screens/flows, metrics, repository | Campaign CRUD; bilingual generation, history, sources, editing/review; basic React welcome/health screen | Full UI workflow, responsive Arabic/English handling, end-to-end evidence, current checks, clean-machine run | P3 with P2/P5 |
| 8. Risk/change log, weekly logs, updated Gantt | Development history and changelog | Start structured weekly logs now; record dated scope changes and update risks/Gantt every week | P5 |
| 9. Final thesis | Material for backend/AI sections | Front matter, all six chapters, consistent citations, references, appendices, formatting | P1 coordinates; all write |
| 10. User/admin manual | README setup instructions | User workflow, operator setup, common failures, maintenance/run guidance, actual access model | P5 with P2 |
| 11. Final pitch deck | No deck found | 10-12 slides covering problem, gap, system, AI, demo, results, impact, ethics, future work | P1 with all |
| 12. Poster/one-pager | No poster found | One page with problem, solution visual, AI contribution, Egyptian context, measured results | P3 with P1 |
| 13. Live defense and demo | Backend Swagger walkthrough recorded | UI hero scenario, rehearsals, each member prepared for questions, honest outage contingency | P5 coordinates; all present |

Existing backend evidence is recorded as 165 passing regression tests. The
13 October pilot used three bilingual requests and produced six language packages.
Mean observed request duration was 50.21 seconds, range 19.64-86.34 seconds.
All three topics needed editorial correction. Review was Codex-assisted, not
an independent human benchmark. Temporary evaluation database rows were rolled
back. Preserve these limitations when reusing results.

## Proposed MVP and completion criteria

Hero scenario: create a traffic-safety campaign, choose Egyptian Arabic/English/both,
enter audience and tone, generate real drafts, inspect the five text fields and
supplied sources, edit a field, review each language independently, and reload
saved history from PostgreSQL.

MVP acceptance:

- Campaign create/read/update/delete works through the frontend with validation.
- Generation uses the real backend/provider; new output is stored as draft.
- Headline, slogan, awareness message, caption, and call to action display correctly.
- Arabic and English direction is correct, including on narrow screens.
- History and source snapshots survive refresh; source context is not described as automatic fact-checking.
- Editing returns a reviewed package to draft; approval/rejection is independent for each language.
- Loading, empty, validation, provider failure, and timeout states are understandable.
- Duplicate generation submissions are blocked while pending; an uncertain connection outcome directs users to saved history before retrying.
- A teammate can reproduce the demo from the run guide on another machine.
- Each requirement has linked implementation and test/demo evidence, or an explicit documented limitation.

Recommended Graduation 1 scope excludes image/video generation, public publishing,
background processing, and production cloud rollout. These are proposed scope
boundaries to confirm with the supervisor. Authentication is currently absent:
document the local controlled prototype and its restrictions honestly. The thesis
mentions authentication/deployment; it does not justify claiming either exists.
If either is explicitly required for our MVP, record the scope change in week 1
and reschedule before adding it.

The PDF requests a private source repository (page 28). Verify current remote
visibility and supervisor expectations in week 1. This plan does not change access.

## Five-person ownership

| Placeholder | Main responsibility | Writing and evidence responsibility | Cross-review partner |
| --- | --- | --- | --- |
| P1 | Coordination, problem definition, literature, thesis editing | Charter; Chapters 1, 2, 6; references; deck narrative | P4 |
| P2 | Backend, integration contracts, database, architecture | Chapter 3 technical design; backend/database/integration parts of Chapter 5; API/operator notes | P3 |
| P3 | Frontend, UI/UX, Arabic/responsive behavior | Wireframes, navigation, frontend Chapter 5 sections, final screenshots, poster design | P2 |
| P4 | AI pipeline, source data, experiments and responsible AI | Chapter 4; research comparison input; raw results, rubric, limitations | P5 |
| P5 | QA, user feedback, evidence management and release preparation | Test cases/results; weekly/risk/change logs; manual; validation Chapter 5 sections; submission checklist | P1 |

These leads organize work; every member contributes writing, reviews another
member's work, and must understand the whole system for defense. P1 integrates
the thesis, rather than writing everyone's technical sections. Check capacity
once names/hours arrive; do not assume equal expertise or unlimited availability.

## Weekly tasks and deliverables

Dates are inclusive and use Cairo local dates. All work below is planned unless
linked evidence shows completion. Each weekly output must include an owner,
reviewer, due date, and evidence link.

### Week 1 17 to 23 October

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Collect existing academic work; draft the 2-3 page charter, Phase 1 report and Chapter 1; identify at least two personas and 3-5 measurable objectives; open a shared reference library and literature extraction table. |
| P2 | Inventory implemented endpoints/entities; draft numbered FR/NFR and traceability matrix; produce initial architecture and ERD from actual code; check supervisor expectations for access/deployment. |
| P3 | Design campaign list/form/workspace, generation/history/review screens and navigation flow; implement app routing, shared API configuration, and server-state foundation using the existing frontend stack. |
| P4 | Consolidate existing pilot/raw evidence; document AI input/output, prompt/source/model versions and limitations; design evaluation rubric, baseline comparison, and evaluation-case catalogue. |
| P5 | Create risk/ethics sheet, risk/change register, weekly log and Gantt; verify repository privacy expectations; collect a fresh baseline test/build report and confirm a second teammate can start the system. |

Gate: agreed MVP and owners, requirements checklist, dated plan/logs, wireframes,
AI evaluation protocol, and initial Chapter 1 draft. Confirm university checkpoint
dates and whether API-based pretrained AI is acceptable as our approved contribution.

### Week 2 24 to 30 October

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Draft Chapter 2 from verified academic/product sources; as a planning target cover 6-8 closely relevant research sources and 3-4 real solutions; build the cited comparison and map supported gaps to MVP requirements. These counts are team targets, not university minima. |
| P2 | Complete formal core use cases with actors, preconditions, main/alternate/error flows; produce context, sequence and DFD diagrams; write Chapter 3 requirements/database/access notes; support CRUD integration. |
| P3 | Implement campaign listing, pagination, creation, viewing, editing and confirmed deletion; handle validation/loading/error/empty states; demonstrate persistence after reload. |
| P4 | Finalize the source/data description and evaluation labels; prepare 12 synthetic briefs covering three current traffic topics, audiences and tones; plan English-only, Arabic-only and bilingual schema coverage separately. |
| P5 | Create test cases with ID, scenario, input, expected/actual output and status; test CRUD; recruit two independent Egyptian Arabic/English reviewers if feasible; prepare consent and user-task forms; update logs/Gantt. |

Gate: functioning campaign UI; cited Chapter 2 draft; analysis pack draft;
evaluation materials reviewed before new experiments. Coordinate reviewer time early.

### Week 3 31 October to 6 November

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Refine Chapters 1-2 after peer/supervisor feedback; remove unsupported novelty claims; audit citation/reference correspondence and maintain a common glossary. |
| P2 | Support generation/history/source API integration; finalize component/class and activity diagrams and entity-field sensitivity notes; explain each diagram in prose and complete Chapter 3 draft. |
| P3 | Implement explicit generation form, pending/timeout/error behavior, bilingual text packages, source display, and saved generation history; prevent duplicate submission and preserve inputs on failures. |
| P4 | Run or arrange the agreed comparison experiment within available quota/budget; retain unchanged raw outputs and metadata; prepare blinded review packets. Report any blocked runs rather than substituting fake model-quality results. |
| P5 | Verify create-to-generate-to-reload integration; test language direction, controlled provider failures and uncertain connection behavior; record actual outputs and defects; arrange user-session dates. |

Gate: real provider generation works through the UI and history survives reload;
Chapter 3 and AI dossier drafts are available for review. Diagram descriptions
must distinguish implemented behavior from planned remaining UI work.

### Week 4 7 to 13 November

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Integrate Chapters 1-4 into one thesis structure; check whether proposed gaps/objectives match the implemented scope; draft discussion notes from actual findings. |
| P2 | Resolve integration defects; write backend/database/API and AI integration parts of Chapter 5; document local deployment, startup, secrets handling, and current access limitations. |
| P3 | Implement partial editing, save feedback, independent approve/reject, and reset-to-draft feedback; finish Arabic/English UI labels, responsive layout, keyboard/focus behavior and core copy actions where included. |
| P4 | Collect independent rubric scores, check disagreement, summarize before/after comparison and weaknesses; complete Chapter 4 with model/configuration justification and responsible-use analysis. |
| P5 | Test the full review lifecycle, including editing previously approved content; run initial user sessions; draft user/admin manual; log findings, consent handling and fixes. |

Gate: the entire hero scenario works; Chapter 4 has measured results and honest
limitations; a full MVP candidate and manual draft exist. Small numbers of reviewers
or users must be reported as exploratory evidence.

### Week 5 14 to 20 November

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Write Chapter 6 discussion/conclusion/future work and draft abstract; consolidate scope changes and evidence-backed contribution claims. |
| P2 | Fix release-blocking backend/integration bugs; have another member verify migrations/setup; finalize installation/operator guidance and API appendix. |
| P3 | Fix observed usability/RTL/responsive problems; freeze the core UI by 20 November; capture final implemented screens and update navigation/UI diagrams. |
| P4 | Finalize evaluation tables and example outputs; rerun affected cases only after relevant AI changes; preserve earlier versions and label exploratory versus final evaluation data. |
| P5 | Complete functional/integration/performance evidence and target 3-5 brief usability sessions if feasible; close critical bugs; finalize test appendix and manual; rehearse an end-to-end run from documented setup. |

Gate: working MVP freeze on 20 November; final screenshots and evaluation evidence
available; no new features without an explicit scope decision. Core flow defects
remain higher priority than visual extras.

### Week 6 21 to 27 November

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Assemble the complete thesis including front matter, six chapters, references and appendices; draft the 10-12 slide pitch narrative; obtain feedback on the full draft. |
| P2 | Audit technical accuracy of Chapters 3/5, all diagrams and run instructions; verify the handover on another machine and document environment differences. |
| P3 | Prepare the one-page poster and slide visuals; ensure all screenshots match the frozen build; check figure numbering and image readability. |
| P4 | Audit Chapter 4, data provenance, result denominators, model/prompt identifiers, citations and AI claims; prepare model-choice/evaluation/bias defense answers. |
| P5 | Compile appendix logs, risks, changes, tests and manual; audit traceability from objectives to requirements to tests/results; run a mock demo and manage the remaining defect list. |

Gate: full thesis draft by 27 November; deck, poster, manual, appendices and
reproducible demo candidate ready. Every deliverable has a reviewer.

### Week 7 28 November to 4 December

| Owner | Tasks and deliverable |
| --- | --- |
| P1 | Resolve thesis feedback; check formal language, chapter openings/summaries and reference consistency; finalize slide narrative and speaking allocation. |
| P2 | Freeze a tested release candidate; review startup/recovery procedures and architecture Q&A; fix only justified blockers and verify affected behavior. |
| P3 | Final visual check of thesis figures, screenshots, poster and deck; repair page breaks, separated captions and unreadable diagrams with P1; rehearse the UI demo. |
| P4 | Rehearse AI explanation and limitations with every teammate; verify no one claims training, automatic factual verification or government approval; check final result consistency across all assets. |
| P5 | Run two timed mock defenses with all five members; verify submission file formats/naming/access, repo handover, manual and final checklist; retain a clearly labeled recording/saved demo as an outage contingency. |

Gate: submission-ready package by 4 December; all five members can explain the
architecture, data, AI choice, evaluation, ethics, limitations and their contribution.

### Submission buffer 5 to 8 December

All members perform a final read and verify their owned material. P1 coordinates
the final upload with the authorized submitter. P2/P3 verify the frozen demo;
P4 verifies results; P5 checks file completeness and records submission evidence.
Use this buffer for corrections and upload problems. Do not schedule new features.
Confirm the university's exact cutoff time and delivery channel before this window.

## Evaluation protocol to complete in weeks 1 to 5

Recommended experiment, subject to available time/quota and supervisor agreement:

- Reuse the three-topic pilot as preliminary evidence, retaining its limitations.
- Use 12 new synthetic briefs, balanced across seat belts, speeding and distracted driving, varying audience and tone within the supported source catalogue.
- Compare a basic prompt baseline and the source-context workflow using the same provider/model, briefs and other settings. Do not vary model and source context simultaneously and attribute the difference to one factor.
- Run two repetitions per condition if feasible: 12 briefs x 2 conditions x 2 repetitions = 48 requests. Bilingual runs yield up to 96 language packages. This is a proposed experiment, not completed work or an authorization to consume quota now.
- Freeze the evaluation inputs before the comparison. Tune prompts using separate development examples; do not tune on the final evaluation cases and present them as unseen.
- Keep raw text, timestamps, errors, model/prompt/source versions and human scores. A source-free baseline remains evaluation-only and is not approved or published.
- Ask two independent reviewers to score anonymized/randomized outputs for factual support against supplied evidence, Egyptian Arabic naturalness, English clarity, bilingual alignment, audience fit and safety. Record scale definitions, disagreement handling and reviewer background.
- Report structural validity and request success as separate rates; unsupported-claim rate, edit-required rate and rubric distributions by language/condition; observed request latency with sample size; user task completion and observed usability issues.
- Define each metric's unit and denominator before scoring: request, brief, language package or claim. Distinguish automatically computed checks from human judgments. Record token/cost information only if actually available.
- Avoid generic classification accuracy/F1 for free-text generation without a defined labeled classification task. Do not use API tests as evidence of text quality.
- Report the sample as a small prototype study. If resources are insufficient, reduce repetitions or briefs transparently before execution and keep comparisons paired; do not imply statistical generalization.

Chapter 4 training methodology should explicitly state that GovReach uses a
pretrained provider API, with no project-specific weight training or fine-tuning
in the current implementation. Explain prompt construction, source selection,
structured output, validation, integration and evaluation. Separate curated
reference material, synthetic evaluation inputs and generated outputs; none is
automatically a model-training dataset. Confirm this approach satisfies the
supervisor's project-specific AI expectations.

## Thesis and diagram checklist

Follow the supplied table of contents rather than inventing a new chapter order:

1. Introduction: motivation, problem, objectives, target users, scope, solution, contributions, thesis organization.
2. Literature review and existing solutions: cited research and products, comparison, supported gaps, project response.
3. Analysis and requirements: roles, FR/NFR, formal use cases, architecture/diagrams, database and UI design.
4. AI integration and methodology: AI role/problem, data/preprocessing, selection/pipeline/configuration, metrics/results/integration/limitations.
5. Implementation and evaluation: environment/tools, frontend/backend/database/AI, integration, actual deployment status, walkthrough, functional/integration/performance/user testing and results.
6. Discussion, conclusion and future work: results, challenges, limitations, achievements and realistic next steps.

Include all diagram types collectively requested across the documents:
high-level architecture, system context, use case, sequence, activity, DFD, ERD,
class/component, UI screens/design and navigation flow. Explain each in text;
use 1-2 explanatory paragraphs for the architecture-pack diagrams. Keep all
diagrams consistent with the final implementation and access model.

Front matter includes title, abstract, acknowledgment, contents, lists of
figures/tables/abbreviations and keywords. Use one reference style, IEEE or ACM,
with real verified sources and matching in-text citations. Start each chapter
on a new page with an introduction and end it with a summary. Use chapter-based
figure/table numbers; figure captions below, table captions above. Reference
and explain every figure/table in the prose. Update automatic contents/lists,
page numbers, spelling and formatting after final edits.

Include Gantt, weekly logs and risk/ethics material as required by the PDF,
even though the generic Word outline describes appendices as optional.
Other appendices include supporting diagrams, API documentation, test cases,
user/admin manual and installation/run guide. Reference them in the main text.

## Weekly operating routine and templates

Start each week by confirming owners and acceptance criteria; use a short
midweek blocker check and a weekly working demonstration/peer review. Update
Gantt, risk/change register and thesis immediately after the review. Record
earlier work only from dated evidence and label retrospective entries; do not
invent historical weekly logs.

Required weekly log columns:

| What we planned this week | What we actually did | Current blockers / risks | Plan for next week + owner |
| --- | --- | --- | --- |
| Fill at week start | Link dated artifacts, commits, tests or reviews | Record impact and action | Name accountable person and due date |

Task tracker fields: ID, requirement/deliverable, task, owner, reviewer, start,
due, status, dependency, acceptance criterion and evidence link. A task is done
when its deliverable exists, its reviewer checks it, and its evidence is linked.

Traceability template:

| Objective or gap | FR/NFR | Use case or module | Diagram or thesis section | Test / metric | Actual evidence / status |
| --- | --- | --- | --- | --- | --- |
| To populate in week 1 | Numbered requirement | Actual implemented behavior | Final document location | Defined pass criterion | Link result or flag gap |

Risk register fields: ID, description, likelihood, impact, mitigation, owner,
trigger, status and review date. Initial candidates: unsupported safety claims,
provider quota/latency, frontend integration delays, weak independent evaluation,
late thesis integration and missing progress evidence. Cover bias, privacy,
consent and government-endorsement risks explicitly. Change records should state
the date, original commitment, change, reason, schedule impact and decision owner.

## Pending inputs and decisions

- Five team members' names, strengths and realistic weekly availability.
- Supervisor confirmation of checkpoint dates, acceptable AI contribution,
  approved MVP boundaries and any mandatory access/deployment features.
- Existing academic documents held outside this repository.
- Exact submission time, upload channel, required formats and presentation length.
- Independent reviewers/user testers and feasible experiment quota/budget.

No code, repository access or external service configuration was changed as part
of preparing this plan. The original university files remain unchanged.
