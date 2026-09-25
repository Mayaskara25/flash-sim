<!-- PLAN.md §6 PR checklist. Fill in and tick before requesting review. -->

## Handoff

- **ID:** H<!-- e.g. H0, H3-fix-templates -->
- **Branch:** `h<N>-<slug>`

## What this PR does

<!-- One or two sentences. -->

## Checklist

- [ ] Acceptance criteria from the handoff doc are met (link/paste them here)
- [ ] `pytest -q` is green (`cd backend && .venv/bin/python -m pytest -q`)
- [ ] `npm run build` is green (`cd frontend && npm run build`)
- [ ] `npm run lint` is green (`cd frontend && npm run lint`)
- [ ] Screenshot or GIF attached, if this PR touches the UI
- [ ] **Contracts changed? y/n** — if yes, `docs/CONTRACTS.md`, `backend/incident/contracts.py` and `frontend/src/incident/types.ts` were all updated together, and both people reviewed it (PLAN.md §6)
- [ ] Only files owned by this handoff were touched (or coordinated first)
- [ ] Fixtures under `docs/contracts/fixtures/` updated if the contract changed

## Notes for the reviewer

<!-- Anything ambiguous you resolved, deviations from the handoff, follow-ups. -->
