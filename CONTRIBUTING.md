# Contributing to GovReach AI

Start with the README and phase documents. Keep changes scoped to a feature or
fix, preserving existing API contracts and applied migration history.

1. Create a descriptive branch, for example `codex/campaign-ui`.
2. Implement a complete change and update relevant documentation.
3. Add meaningful tests for new workflows or failure handling.
4. Run backend tests and frontend build/lint as applicable.
5. Open a pull request explaining the problem, behavior, and validation.

Use messages such as `feat(frontend): add campaign creation form`,
`fix(ai): handle provider timeouts`, or `docs: explain source review`.
Avoid combining unrelated changes or rewriting shared commit history.

Backend check, from `backend`: `.venv/Scripts/python.exe -m pytest -q`.
Frontend checks, from `frontend`: `npm run lint` and `npm run build`.
Automated tests use fake providers and isolated databases; paid/live checks are
explicit local commands, never routine CI steps.

- Add an Alembic revision for schema changes; do not edit applied migrations.
- Preserve generation history and source snapshots.
- Editing resets content to draft; approval does not publish it.
- Commit only synthetic, reviewed evaluation examples; redact personal data.
- Never commit `.env`, tokens, private keys, database dumps, environments, or builds.

Agree on major architectural changes before implementation. Authentication and
institutional content approval remain future work.
