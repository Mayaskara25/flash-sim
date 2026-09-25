# MochaTrade Flash-Crash Console: Master Plan

> **This is the document everyone follows.** If a handoff, a PR or a chat message disagrees with this file, this file wins. Change it by PR, not in DMs.

| | |
|---|---|
| Event | ACM MarketSphere 2026, Round 2, **Track 3: The Flash-Crash Simulation** (`ROund2/ACM_MarketSphere_Round2_Build.pdf`) |
| Design input | `docs/SPEC.md` (generated from `ROund2/MochaTrade Flash-Crash Scenarios & Response Spec.docx`) |
| Interface contract | `docs/CONTRACTS.md` |
| Work packages | `docs/handoffs/H0…H10` |
| Base repo | P2 Risk Engine (FastAPI + React/TS/Tailwind/Recharts) — see `REPO_EXPLAINED.md` |

---

## 1. What we are building (one paragraph)

A **one-screen incident console** for MochaTrade's 3-person ops team (IC = Incident Commander, TL = Tech Lead, CS = Comms/Support) that replays a scripted flash crash in simulated real time. It shows the 4–6 signals that matter right now, computes a live severity (SEV-4…SEV-1) with hard overrides and hysteresis, classifies **market vs system** cause via the liquidation anomaly ratio (LAR), proposes at most 3 next actions per role, surfaces pre-filled communication templates that need a named approver, and writes every alert, decision and message to an append-only incident log that generates the final summary. On top of the spec, it adds a **prediction layer**: an escalation forecast, an insurance-fund runway, and a what-if on each proposed control, built from the repo's existing cascade model and Monte Carlo engine.

## 2. How this maps to the judging brief

| Brief must-have | Where it is delivered | Handoff |
|---|---|---|
| Live or simulated feed of ≥ 2 signals | Scenario timelines + book-driven LIQ_RATE / LAR / INS_FUND + scripted TICKET_RATE, SENTIMENT, STBL_PX, … (20 signals) | H1 |
| Alert thresholds / escalation triggers | Signal thresholds, severity score S, hard overrides, state machine with hysteresis | H2 |
| Pre-built communication templates | T1–T12, auto-surfaced, live-filled, approve/edit/send | H3, H4, H5 |
| Running incident log incl. abnormal-liquidation decisions | Append-only log (§12.1 schema) with `liquidation_review`; generated summary | H5, H6 |

| Judging focus | Our answer |
|---|---|
| Speed and clarity under a live scenario | One screen, 4 zones, sim clock 1×–10×, C1 demo in ~8 min |
| Supports the Round 1 response plan, not just data viz | Playbooks drive actions; the tool proposes, a human approves, the log records who and why |
| Realism for a 3-person team | Role tabs (IC/TL/CS), max 3 actions visible per role, runbook phases |
| Reduces chaos | Show only the signals relevant to active tags, collapse repeated alerts, forecast warns *before* thresholds are crossed |

**Extra feature (prediction):** "SEV-1 likely in ~6 min (p≈0.7)", "insurance fund reaches 25% in 9–14 min", and "approving reduce-only drops P(SEV-1 in 15 min) from 68% to 21%". Labelled *simulated projection*. See H7.

## 3. Decisions already made (do not reopen without a PR to this file)

1. **Stack stays as is.** FastAPI + NumPy/scikit-learn backend, React 19 + TS + Tailwind 4 + Recharts frontend. No new frameworks, no database, no WebSocket.
2. **Transport = polling.** Frontend polls `GET /api/incident/state` every 1 s (wall time). Operator actions are POSTs that return the full new state.
3. **Clock lives in the backend.** Sim time advances lazily from wall-clock × speed on each request (no background threads). One tick = 2 sim-seconds. Given the same scenario, seed and operator inputs, the run is deterministic.
4. **New code goes in a new package `backend/incident/`** and a new frontend folder `frontend/src/incident/`. Existing modules are *imported*, not rewritten.
5. **LIQ_RATE and LAR are computed from the synthetic book** (existing `simulation/portfolio.py` + `liquidation/model.py`). That is what makes the tool MochaTrade-specific rather than a random-number dashboard. Other signals may be scripted keyframes.
6. **One incident, many tags.** A single incident object carries several active scenario tags (M1, I1, M2…). It never becomes several incidents.
7. **Severity level is derived from state.** `state = max(state_from_thresholds, state_from_score S, EMERGENCY if any hard override)`, then Emergency = SEV-1, Critical = SEV-2, Warning = SEV-3, Watch/Normal = SEV-4. Upward moves are automatic; downward moves need 5 sim-minutes below band plus IC confirmation.
8. **The tool proposes, a human approves.** No control and no customer or public message takes effect without an `approved_by` role. Controls have effects on the simulation (via H3's effect catalogue), so approving reduce-only visibly slows the cascade.
9. **C1 "Black Tuesday" is the demo spine.** With reduce-only approved by ~T+18, C1 peaks at SEV-2 and resolves by T+55. With no action, the fund crosses 25% → SEV-1 around T+24. The spec's "peak SEV-1" label for C1 describes that no-action branch, and the forecast/what-if feature exists to show it.
10. **Console becomes the landing page (`/`).** The existing 7 pages move under `/analyst/*` as drill-downs, reachable from signal cards. They are not deleted.
11. **All numbers are prototype assumptions** (spec §13.3). The UI shows a persistent "SIMULATION" badge and an Assumptions panel.
12. **Roles in the UI:** a role switcher (All / IC / TL / CS). There is no auth; the actor is whoever the switcher says.

## 4. Architecture

```
                         ┌───────────────────────── backend/incident/ ─────────────────────────┐
 scenarios/*.json ──▶ clock.py ──▶ signals.py ──(SignalFrame)──▶ rules/ ──▶ playbooks/templates ──▶ session.py ──▶ api.py (/incident/*)
                          │          ▲   │                         severity   (H3 content)          │  log.py         │
                          │          │   └─ book.py (reprices existing   classifier                  │  summary.py     │
                          │          │       synthetic book: LIQ_RATE,   state_machine                │                 │
                          │          │       LAR table, bad debt)        tags, alerts                 │                 │
                          │          └──── control effects (approved controls modify the sim) ◀────────┘                 │
                          └──────────────▶ forecast.py (H7): ensemble of projected frames → same rules → probabilities ────┘
                                             reuses cascade_model/ + monte_carlo/ ideas

 frontend/src/incident/: api.ts + types.ts ──▶ useIncident() poller ──▶ IncidentConsole (4 zones) ──▶ /analyst/* (existing pages)
```

The pure-function boundaries (SignalFrame in, verdicts out) are what let the handoffs run in parallel. They are fixed in `docs/CONTRACTS.md`.

### Screen: four zones (spec §9.5)

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ ① SEV-2 CRITICAL  ·  T+14:32  ·  tags [M1][I1][M2]  ·  verdict: MARKET-DRIVEN (LAR 1.1)     │
│    Forecast: SEV-1 in ~6 min (p 0.68) · Ins. fund → 25% in 9–14 min      [1× 5× 8× 10×] ⏸ │
├─────────────────────────────────┬─────────────────────────────────────────────────────────┤
│ ② ACTIVE SIGNALS (4–6 cards,    │ ③ NEXT ACTIONS — role: [All|IC|TL|CS]  (max 3 each)     │
│    sparkline, threshold lines,  │   IC ▸ Reduce-only on NVDA-PERP   P(SEV-1) 68%→21%      │
│    collapsed alert counters)    │        [Approve] [Skip]  rationale required             │
│    LIQ_RATE 410/min ▲ CRIT      │   CS ▸ T3 reduce-only notice (pre-filled) [Edit/Send]   │
│    INS_FUND_PCT 40% ▼ WARN      │   TL ▸ Confirm liq engine not over-firing (rule out P1) │
│    TICKET_RATE 6× ▲ WARN        │                                                         │
│    LAR 1.1 · normal             ├─────────────────────────────────────────────────────────┤
│    [+14 more collapsed]         │ ④ INCIDENT LOG (append-only, newest first, filterable)  │
│                                 │   T+14:32 transition WARNING→CRITICAL  system           │
└─────────────────────────────────┴─────────────────────────────────────────────────────────┘
```

## 5. Phases, handoffs and execution order

### 5.1 Handoff list

| ID | Title | Area | Size | Depends on | Suggested owner |
|---|---|---|---|---|---|
| **H0** | Foundation: contracts, stubs, fixtures, CI, Linux start | both | S | — | **A (you)** |
| **H1** | Sim clock, scenario timelines, book-driven signal generator | backend | L | H0 | **A** |
| **H2** | Rules engine: severity, overrides, classifier, state machine, tags, alerts | backend (pure) | M | H0 | **A** |
| **H3** | Playbooks, protective controls (+ effects), templates T1–T12 | backend (pure/content) | M | H0 | **B (teammate)** |
| **H4** | Frontend console shell on fixtures (4 zones, role switcher, routes) | frontend | L | H0 | **B** |
| **H5** | Incident session, operator API, log, summary (integration) | backend | M | H1, H2, H3 | **A** |
| **H6** | Frontend live wiring: polling, operator actions, modals, errors | frontend | M | H4, H5 | **B** |
| **H7** | Prediction: escalation forecast, fund runway, control what-if | backend | M | H5 | **A** |
| **H8** | Scenario pack C2–C6 + live injects + golden tests | backend (content) | M | H5 | **A** or **B** |
| **H9** | Frontend: forecast strip, what-if badges, summary view, assumptions, anti-chaos polish | frontend | M | H6 (+ H7 contract; fixtures OK) | **B** |
| **H10** | Demo hardening: rehearsal, README, analyst sync, final checklist | both | S | all | **A + B** |

### 5.2 Execution order (dependency graph)

```
Phase 0 (sequential, blocks everyone)        H0
                                              │  merge to main
                     ┌──────────────┬─────────┼──────────────┐
Phase 1 (parallel)   H1             H2        H3             H4
                     │              │         │              │
                     └──────┬───────┴─────────┘              │
Phase 2 (integration)       H5 ─────────────────────────────▶ H6
                            │                                 │
                     ┌──────┴──────┐                          │
Phase 3 (parallel)   H7            H8                         H9
                     └──────┬──────┴──────────────────────────┘
Phase 4                     H10
```

**Critical path:** H0 → H1 → H5 → H7 → H10. Anything on it slipping moves the demo, so A owns it.

### 5.3 Two-person schedule (what runs in parallel)

| Slot | A (you) — backend core | B (teammate) — content + frontend | Merge gate at end of slot |
|---|---|---|---|
| 0 | **H0** | read SPEC §3, §9–12 + CONTRACTS; set up env | H0 merged → B can start |
| 1 | **H1** (clock, scenarios, book signals) | **H3** (playbooks/controls/templates, pure, fixture-tested) | H3 merged |
| 2 | **H2** (rules engine) | **H4** (console on fixtures) | H1, H2 merged |
| 3 | **H5** (session + API) | **H4** cont. → start **H6** against the H0 stub API | H4, H5 merged |
| 4 | **H7** (forecast) | **H6** (live wiring) | H6 merged → **first full C1 run end to end** |
| 5 | **H8** (C2–C6) | **H9** (forecast UI, summary, polish) | H7, H8, H9 merged |
| 6 | **H10** together: rehearse C1 twice, fix, freeze | | tag `demo-v1` |

If a third pair of hands (or an AI agent) is available, give them **H2** in slot 1 and **H8** in slot 4. They are pure and well fenced.

### 5.4 Milestones (definition of done per phase)

- **M0 — Contracts frozen (end of Phase 0):** `GET /api/incident/state` returns fixture JSON that validates against the pydantic models; the frontend renders it; CI green.
- **M1 — Engines unit-tested (end of Phase 1):** C1 replays headless with correct signal markers (H1). Rules reproduce spec thresholds (H2). Playbooks and templates render (H3). Console renders all fixtures (H4).
- **M2 — Walking skeleton (end of Phase 2):** C1 runs live in the browser from start to resolution with operator clicks. The golden test `test_c1_scripted_operator_run` passes.
- **M3 — Feature complete (end of Phase 3):** forecast and what-if visible; C2–C6 selectable; summary page.
- **M4 — Demo ready:** two clean rehearsals of the §12.2 script at 8×, with the assumptions stated.

## 6. Repo, branches and PR rules

- Default branch **`main`**, with protected merges via PR (turn on branch protection after you create the GitHub repo).
- **One branch per handoff:** `h<N>-<slug>`, e.g. `h3-playbooks`, `h4-console-shell`. Small follow-ups use `h<N>-fix-<slug>`.
- **File ownership** is listed in each handoff under *You own*. Do not edit files owned by another open handoff. If you must, coordinate first and keep the diff tiny.
- **Contract changes** (`docs/CONTRACTS.md`, `backend/incident/contracts.py`, `frontend/src/incident/types.ts`) must change **all three together** in one PR, and both people review it. Additive changes (new optional fields) are cheap; renames and removals are not.
- **PR checklist** (in `.github/pull_request_template.md` from H0): handoff ID, acceptance criteria ticked, `pytest` green, `npm run build` + `npm run lint` green, screenshot/GIF for UI, "contracts changed? y/n".
- Rebase on `main` before merging; squash-merge; delete the branch.
- Commit messages: `H3: add M2 playbook and reduce-only control`.

## 7. Testing strategy

| Layer | Tool | What |
|---|---|---|
| Rules (H2) | pytest | Threshold table tests generated from SPEC §9.1; override cases; hysteresis timing; classifier truth table from §9.2 |
| Content (H3) | pytest | Every tag has a playbook; every template placeholder is resolvable from a state fixture; action ordering follows the §8 priority rule |
| Signals (H1) | pytest | Determinism (same seed → same frames); C1 markers within tolerance; book LAR ≈ 1.0 for pure market moves |
| Integration (H5, H8) | pytest golden runs | Scripted operator inputs replayed → expected states at expected times; summary matches the log |
| Forecast (H7) | pytest | Leads SEV-1 by ≥ 3 sim-min on the C1 no-action branch; what-if lowers P(SEV-1) for reduce-only; < 150 ms per compute |
| Frontend (H4, H6, H9) | `npm run build`, `npm run lint`, manual script | Fixture mode (`VITE_INCIDENT_MOCK=1`) renders every fixture state; manual C1 walkthrough checklist |

CI (GitHub Actions, added in H0) runs `pytest` and `npm ci && npm run build && npm run lint` on every PR.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Book-driven LIQ_RATE doesn't hit spec magnitudes (100/300 per min) | `book_scale` calibration factor in the scenario JSON; H1 acceptance uses tolerances; scripted fallback allowed for INS_FUND only |
| Parallel work drifts from the contract | H0 fixtures plus pydantic validation in CI; the frontend builds against the same fixtures |
| Severity flaps during the demo | Hysteresis is in the spec; H2 tests it explicitly |
| The demo runs long | Speed control; C1 tuned to ~8 min at 8×; "jump to T+14" debug control (H6) |
| Forecast too slow or noisy | Compute every 5 ticks, cache, N=200 ensemble, fixed seed per tick |
| Too much on screen | Hard caps in the contract: ≤ 6 signal cards expanded, ≤ 3 actions per role |
| Judges question realism of the numbers | Assumptions panel + SPEC §13.3 read aloud at the start of the demo |

## 9. Out of scope

Real exchange/ticketing/social integrations, auth, persistence across restarts, mobile layout (desktop and projector first), actually sending messages anywhere (the "send" action logs only), and anything about Tracks 1, 2 and 4–6.

## 10. Glossary

IC/TL/CS = the 3 roles · LAR = liquidation anomaly ratio (observed ÷ expected liquidations) · ADL = auto-deleveraging · reduce-only = users may close but not open positions · tag = scenario ID from SPEC §4 (M1…I2) · chain = compound scenario C1–C6 (SPEC §8) · tick = 2 sim-seconds.
