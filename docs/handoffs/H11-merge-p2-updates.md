# H11: Merge the "P2 updates" (voice copilot, liquidation investigator, PDF report)

| | |
|---|---|
| Branch | `h11-p2-updates` (already created and imported, see below) |
| Owner | A |
| Size | S (mostly done) |
| Depends on | main @ `1ff1f58` |
| Blocks | H12–H16 (UI plan) |

## What arrived
A teammate sent a zip (`flash-sim-2/flash-sim`, a full clone). Their work came in two parts:
- **Committed** `06516de` on their branch `p2-risk-updates`, based on H8 (`dbbc140`), one commit behind main. It adds 8 frontend components: `AICopilot`, `RiskBrief`, `P2ActionQueue`, `TeamStatus`, `IncidentTimeline`, `LiquidationInvestigator`, `IncidentReport`, plus types/api/useIncident changes.
- **Uncommitted:** `backend/incident/command.py` (command brief, action queue, team, investigator data), `copilot.py` (a rule-based Q&A over live state, **no external LLM**), `report.py` (a dependency-free PDF writer) and `tests/test_p2_command.py`. Also edits to `api.py` (new endpoints `POST /incident/copilot`, `GET /incident/report.pdf`, `POST /incident/liquidations/{id}/decision`, `POST /incident/queue/{id}/record`), `session.py`, `contracts.py`, `book.py` (fill tracking for the investigator only; C1 calibration untouched), `CONTRACTS.md` and regenerated fixtures.
- Voice uses the browser's **Web Speech API**: `speechSynthesis` for "Brief me", and speech recognition for "Ask". No keys or network.
- Every file had been converted to **CRLF** line endings (Windows), so `git status` showed ~120 files modified. Only 30 files really changed.

## Already done (by the orchestrator)
1. Fetched their commit into this repo, and imported the uncommitted files with CRLF → LF normalised (the generated `output/pdf/*.pdf` was excluded).
2. Rebased onto `main` (`1ff1f58`, which includes H10) with no conflicts.
3. `pytest -q`: **153 passed** (151 existing + 2 new; the C1 calibration/integration tests still pass). `npm run build` and `npm run lint` are green.

Branch `h11-p2-updates` = main + 2 commits (`Add P2 risk engine incident response updates`, `import: … (CRLF normalised)`) + this docs commit.

## Remaining tasks
- [ ] **Browser check** (`./start.sh`, C1 at 8×):
  - "Brief me" speaks in Chrome and Edge.
  - "Ask" by voice works in Chrome. Firefox has no speech recognition, so the button must hide or disable itself there, not error.
  - Typed questions work: "what should I do first", "what changed in the last 5 minutes", "why was this flagged".
  - `GET /api/incident/report.pdf` opens after RESOLVED and the PDF text is readable.
  - The liquidation investigator's decisions show up in the incident log.
- [ ] **Contract sync:** confirm `docs/CONTRACTS.md`, `backend/incident/contracts.py` and `frontend/src/incident/types.ts` agree on the new types (`CommandBrief`, `ActionQueueItem`, `TeamMember`, `ExecutionView`, `InvestigationCluster`, `CopilotReply`, and the new bodies). The fixture test passes, so the backend matches the fixtures; the TS side needs checking by eye.
- [ ] **Stop CRLF from coming back:** add `.gitattributes` with `* text=auto eol=lf` and `*.png binary`, and ask Windows teammates to run `git config core.autocrlf input`.
- [ ] **Clean up:** delete the `flash-sim-2/` folder from the repo root after merging (it's an untracked 543 MB copy). Also add `output/` to `.gitignore`.
- [ ] Open a PR `h11-p2-updates → main` and merge it.

## Known issues handed to the UI plan (don't fix here)
- The console now renders ~13 panels, and several duplicate each other (see `docs/UI_PLAN.md` §3).
- The timeline labels people **P1/P2/P3**, which collide with scenario tags P1/P2/P3. Fixed in H14.
- "P2" also names the product (P2 Risk Engine), the scenario tag P2 and the role label. Fixed in H14 (use "MochaTrade Ops Console"; roles are IC/TL/CS only).
