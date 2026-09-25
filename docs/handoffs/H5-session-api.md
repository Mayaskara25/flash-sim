# H5: Incident session, operator API, log, summary (integration)

| | |
|---|---|
| Branch | `h5-session-api` |
| Owner | A |
| Size | M (critical path) |
| Depends on | H1, H2, H3 |
| Blocks | H6 (live), H7, H8 |

## Goal
Wire clock → signals → rules → content into one `IncidentSession` singleton behind the real `/incident/*` endpoints, replacing the H0 stub. Every alert, transition, decision and message becomes an append-only log entry (SPEC §12.1). Generate the incident summary from the log.

## Read first
SPEC §3, §9.3–9.5, §10, §12 · CONTRACTS §5, §7 · H1 `SCHEMA.md`, H2 module docstrings, H3 `propose()`/`render()`

## You own
`backend/incident/session.py`, `backend/incident/log.py`, `backend/incident/summary.py`, `backend/incident/api.py` (replace the stub), `backend/tests/test_session.py`, `backend/tests/test_api.py`, `backend/tests/test_c1_golden.py`

## Design
- `IncidentSession` holds: scenario, `SimClock`, `SignalGenerator`, `SignalHistory`, `StateMachine`, tag tracker, alert tracker, actions (id → ActionView), templates (id → TemplateView), active controls, log, and a forecast slot (H7).
- **`advance()`**, called at the start of every request: for each pending tick → `frame = gen.step(t, active_effects)` → history.push → classify → score → state step → tags/alerts update → log new alerts and transitions (`actor: system`) → `propose()` → merge into actions (new ones `proposed`, never duplicate an existing id) → template triggers → expire time-boxed controls (log + review action). Cap the catch-up per request at 600 ticks; when the clock ran ahead, process in a loop (≤ 50 ms budget at 10×).
- **Operator handlers** (validate, then mutate, then log):
  - `decide(action_id, decision, actor, rationale)`: 422 if rationale is empty for approve/skip. On approve with a `control_id`, activate the control (effects start next tick) and log a `decision` with `approved_by`, `expires_at` and `signal_snapshot` (top 6 relevant signals).
  - `send(template_id, actor, text)`: log type `comm` with the final text; that template won't resurface for the same trigger episode.
  - `ack(alert_id, actor)`, `note(actor, text)`, `manual_raise`, `confirm_pending` (IC only; 409 otherwise), `review_liquidations(verdict, ...)` (log with `liquidation_review`), `inject(event)` (appends a temporary track overlay for 5 sim-min, e.g. `stablecoin_dip` → STBL_PX to 0.982 and back).
- **`to_dto()`** builds `IncidentStateDTO`: mark `relevant` signals (tag trigger or status ≥ watch), sort them, include ≤ 10 min history, compute `reminders`.
- **`summary.py`:** built purely from the log: transitions timeline, peak per signal (from history), decisions, comms, liquidation reviews, and open items (unreviewed abnormal liquidations, active time-boxed controls, compensation review needed if any `wrongful`). Also a `markdown` rendering.
- **Thread safety:** a module-level `threading.Lock` around the session (uvicorn may run requests concurrently).

## Tasks
- [ ] Session, log, summary, real API; keep the endpoint shapes identical to CONTRACTS §7.
- [ ] `test_api.py`: every endpoint returns a DTO that validates; 409/422 paths.
- [ ] **Golden test** `test_c1_golden.py`, a headless scripted operator run of SPEC §12.2 using a fake clock:
  - T+0:30 IC acks, approves the leverage cap; T+6:30 CS sends T1 and T11; T+14:40 IC approves reduce-only; CS sends T3.
  - Expect WARNING by T+1, CRITICAL by T+15, **never EMERGENCY**, a pending stepdown by ~T+40, IC confirms → STABILISING, a pending resolve by ~T+55, IC confirms → RESOLVED.
  - Summary lists 2 control decisions, ≥ 4 comms, and liquidation review `market-explained`.
  - Variant: no reduce-only → EMERGENCY with the "Insurance fund below 25%" override between T+20 and T+28.

## Acceptance criteria
- Golden tests green and deterministic (run 3×).
- `GET /incident/state` p95 < 60 ms at 10× speed on a laptop.
- The frontend H4 console, pointed at the live API (turn off mock), renders without code changes.

## Out of scope
Forecast math (H7). Leave `forecast: null` plus a hook `session.forecaster` that H7 plugs into.
