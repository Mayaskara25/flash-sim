# H6: Frontend live wiring

| | |
|---|---|
| Branch | `h6-frontend-live` |
| Owner | B (teammate) |
| Size | M |
| Depends on | H4 (merged); H5 for real data. Can start against the H0 stub API. |
| Blocks | H9, H10 |

## Goal
Make the console drive the real backend: poll state, send operator actions, and handle errors and latency so it feels instant under a live demo.

## Read first
CONTRACTS §5, §7 · H4 `useIncident.ts` header · SPEC §12.2 (the demo you're enabling)

## You own
`frontend/src/incident/useIncident.ts`, `frontend/src/incident/api.ts` (fixes only), `frontend/src/incident/components/*` (behaviour changes), `frontend/src/incident/Toasts.tsx`, `frontend/src/incident/shortcuts.ts`

## Tasks
- [ ] **Polling:** `GET /incident/state` every 1000 ms while the tab is visible (pause on `visibilitychange`), with in-flight dedupe (never two concurrent polls). Stale indicator if the last success was > 3 s ago.
- [ ] **Operator actions:** every button calls the API and replaces state with the response. Disable the button while pending; on error, toast `detail` and keep the modal open with the user's text intact.
- [ ] **Optimistic feel:** after approve/send, immediately grey out the card (pending state) until the response arrives.
- [ ] **Scenario start:** ScenarioPicker loads `GET /incident/scenarios`; Start sends `{scenario_id, speed: 8}`. Show a 3-2-1 pre-roll using `t < 0`.
- [ ] **Clock controls:** pause/resume/speed; a debug "jump" (hidden behind `?debug=1`) with buttons T+0, T+6, T+14, T+35, T+55 for rehearsals.
- [ ] **Keyboard shortcuts** (shown in a `?` overlay): `1/2/3/0` switch role IC/TL/CS/All; `A` approve the top action for the current role (opens the modal with the rationale pre-filled; Enter submits); `S` skip; `N` add a note; `Space` pause/resume.
- [ ] **Role realism:** the actor on every POST is the current role; in "All" view the actor is the action's own role.
- [ ] **Pending confirmation card:** IC confirm → `POST /incident/pending/confirm`.
- [ ] **Liquidation review control** → `POST /incident/liquidations/review`.
- [ ] Keep mock mode working (`?mock=1`) for offline UI dev.

## Acceptance criteria
- A full C1 run at 8× driven only from the UI reaches RESOLVED, with the log showing every click and a named actor and rationale.
- No UI freeze when the backend restarts mid-run: a stale banner appears, then recovery.
- `npm run build` and `npm run lint` green; a GIF of the run in the PR.

## Out of scope
Forecast visuals and the summary page (H9).
