# H7: Prediction layer (escalation forecast, fund runway, control what-if)

| | |
|---|---|
| Branch | `h7-forecast` |
| Owner | A |
| Size | M |
| Depends on | H5 (can prototype offline on H1+H2 earlier) |
| Blocks | H9 (real data; H9 can start on fixtures) |

## Goal
The "extra" feature. Answer three questions every ~10 sim-seconds, using the **same rules engine** on an ensemble of projected futures, and reusing the repo's existing cascade model and Monte Carlo approach:
1. *How likely is each SEV level in 5/10/15 min, and when does SEV-1 arrive?*
2. *When does the insurance fund hit 25%?* (the SEV-1 override)
3. *For each proposed control, how much does approving it change (1) and (2)?*

The point for the judges: the tool warns *before* thresholds are crossed and quantifies the trade-off of each decision, so the team acts on the forecast instead of reacting to a red screen.

## Read first
CONTRACTS §6 · `backend/cascade_model/model.py`, `backend/monte_carlo/engine.py` · H1 `book.py` + effects, H2 `severity`/`state_machine` APIs · H5 `session.forecaster` hook

## You own
`backend/incident/forecast.py`, `backend/tests/test_forecast.py`, the `session.forecaster` wiring line in `session.py` (coordinate with whoever owns H5 follow-ups)

## Method
1. **Snapshot** the generator state (book liquidated mask, fund, histories) with a cheap `copy()` added in H1's classes. If H1 lacks it, add `snapshot()`/`restore()` there in this PR with A's approval.
2. **Price paths:** N = 200 paths × 15 min of ticks (use 10 s steps for speed: 90 steps). Drift = current PX trend over the last 3 min, decaying to 0 with a 10-min half-life. Vol = realised vol over the last 5 min × `VOL_MULT` of the scenario's regime. Shocks follow the `monte_carlo/engine.py` style (normal log returns, seeded `rng(seed + tick)`).
3. **Non-price signals:** extrapolate the last-3-min linear trend with the same decay plus scaled noise; clamp to physical ranges.
4. **Run each path** through a lightweight copy of the book (vectorise across paths as in `monte_carlo/engine.py`: `[paths × positions]` liquidation matrix per step) → LIQ_RATE, bad debt → INS_FUND_PCT. Then feed the frames through H2 `score()` + `StateMachine` in "no-hysteresis projected" mode (upward moves only) → state per horizon.
5. **Cascade model as a driver:** call the existing `cascade_model.evaluate(features)` with features built from the current book (see `SimulationEngine.cascade_features`). Report `cascade_model_p`. Use it to scale the drift of the top-decile paths (fat left tail when the model says a cascade is likely): `drift_tail = drift × (1 + cascade_p)`. Document this; it's where the ML earns its place.
6. **Outputs:** `sev_probs` per horizon, `eta_sev1_min` (p50/p90 of first SEV-1 time among paths that reach it, `prob_within_15`), `ins_fund` quantiles, `eta_fund_25_min`, `drivers` (top 3 signals by contribution to projected S, with a text reason), and a `headline`.
7. **What-if:** for each visible proposed action with a `control_id`, rerun with that control's effects applied from now, reusing the same random draws (common random numbers, so the delta is not noise). Fill `ActionView.what_if` in `to_dto()`.
8. **Budget:** compute every 5 ticks; cache by tick; baseline + ≤ 3 what-ifs < 150 ms total. If over budget, drop N to 100 for the what-ifs.

## Acceptance criteria
- **Lead time:** on the C1 no-action branch, `eta_sev1.prob_within_15 > 0.5` at least **3 sim-minutes before** the actual EMERGENCY transition.
- **Calibration sanity:** on the C1 with-reduce-only branch, P(SEV-1 in 15 min) stays < 0.3 after T+20.
- **What-if direction:** at T+14 in C1, reduce-only lowers P(SEV-1 in 15 min) by ≥ 0.25; an ins_fund_topup of 20% raises the fund p50.
- **Determinism:** same tick → same forecast.
- **Performance** within budget (test with timing).
- The label is always present: `'Simulated projection — not a market forecast'`.

## Out of scope
UI (H9). Training new ML models: reuse the existing one.
