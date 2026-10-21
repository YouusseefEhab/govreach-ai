# Phase 4 verification — 2026-10-21

## Core workflow: user-confirmed

The user reported that the complete frontend workflow passed: campaign creation,
editing and deletion, generation, saved-content editing, separate review decisions,
persistence after reload, draft reset after editing approved text, other-language
preservation, unsaved-edit warnings, and deletion confirmation. This is user-reported
manual verification, not an automated browser run.

## Automated evidence

- 46 frontend tests: API handling, partial updates, review separation, validation,
  directional content, translated screens/catalogue, preference storage, and
  exact clipboard text with denied/unavailable clipboard handling.
- Production TypeScript/Vite build and source lint pass.
- Backend's 165 tests and fake-provider PostgreSQL diagnostic passed in previous
  increments. No backend or schema changes in this polish increment.
- Existing records were preserved; no live Gemini calls for implementation checks.

Build has a non-blocking advisory for a JavaScript chunk above 500 kB. Route
splitting is an optional performance follow-up, not a failed build.

## Interface and accessibility review

Arabic is the initial UI language; explicit preference persists locally. English
uses LTR, Arabic uses RTL. Campaign language and stored text remain independent.
Switching updates existing components without changing their keys or remounting
forms; it does not intentionally discard edits or submit AI requests. Known UI
validation messages and feedback follow the preference. Source titles/sections
remain as supplied. Copy uses saved text, not unsaved editor input.

Code review checked responsive breakpoints, logical spacing, wrapping long source
text/IDs, independent content direction, labelled native controls, focus styling,
status/error announcements, skip navigation and keyboard-focusable table scrolling.
Small footer/ID text contrast was improved. These are code checks, not a visual or
screen-reader accessibility certification.

## Remaining manual checks

Browser control cannot initialize (`failed to write kernel assets`), so these new
controls and layouts still require checks in the running app:

1. Switch to English; check labels/LTR. Refresh to confirm preference persistence,
   then return to Arabic. Campaign language must stay unchanged. Switch while
   editing: retain text, dirty state and the review lock.
2. Copy Arabic/English fields and paste into a text editor. Check punctuation,
   line breaks and emojis. Copy all text and check five-field order. Clipboard
   denial must show failure rather than success.
3. At about 375 px and 768 px, inspect both UI languages, forms, cards, source text
   and editor stacking. Tables may scroll inside their container; the whole page
   should not overflow horizontally.
4. Use Tab/Shift+Tab/Enter/Space through skip navigation, language selector, forms,
   copy buttons, source disclosures, review and confirmations. Focus must be
   visible. Cancel a navigation warning and retain edits.

Phase 4 features are implemented. Final sign-off is pending these new-control,
mobile and keyboard checks. Deployment, authentication, media generation and
institutional publishing are separate later milestones.
