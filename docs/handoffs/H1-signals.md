# H1: Sim clock, scenario timelines, book-driven signal generator

| | |
|---|---|
| Branch | `h1-signals` |
| Owner | A |
| Size | L (critical path) |
| Depends on | H0 |
| Blocks | H5, H7, H8 |

## Goal
Given a scenario JSON, a seed and a list of active control effects, produce a deterministic `SignalFrame` for every tick (2 sim-seconds). LIQ_RATE, LAR, BAD_DEBT_RATE, INS_FUND_PCT and NEG_BAL_ACCTS come from the existing synthetic book being repriced along the scenario's price path. Everything else comes from scripted keyframes plus seeded noise.

## Read first
SPEC §2, §8, §9.1, §9.2, §12.2 · CONTRACTS §2–4 · `backend/simulation/portfolio.py`, `backend/liquidation/model.py`, `backend/simulation/market.py`, `backend/monte_carlo/engine.py` (for the beta-to-asset price mapping)

## You own
`backend/incident/clock.py`, `backend/incident/book.py`, `backend/incident/signals.py`, `backend/incident/scenario_loader.py`, `backend/incident/scenarios/C1_black_tuesday.json`, `backend/incident/scenarios/SCHEMA.md`, `backend/tests/test_clock.py`, `backend/tests/test_book.py`, `backend/tests/test_signals_c1.py`

## Design

**Clock (`clock.py`).** `SimClock(speed, started_wall, paused, t0)`. `now_t()` = sim seconds from wall time × speed. `ticks_until(t)` yields the tick indices not yet processed. `jump(t)` seeks forward only. Wall time is injectable (`time_fn`) so tests never sleep.

**Scenario JSON (`scenarios/*.json`, documented in `SCHEMA.md`):**
```json
{
  "id": "C1", "name": "Black Tuesday", "description": "...",
  "preroll_s": 120, "duration_s": 3600, "seed": 42, "asset": "NVDA",
  "book": { "n_traders": 10000, "avg_leverage": 14.7, "long_ratio": 0.72,
            "book_scale": 1.0, "insurance_fund_usd": 250000, "slippage": 0.35 },
  "tracks": {
    "PX":          [[-120, 0.0], [0, -0.06], [840, -0.11], [2100, -0.07], [3300, -0.03]],
    "TICKET_RATE": [[-120, 1], [360, 4], [900, 6], [2400, 2], [3300, 1]],
    "SENTIMENT":   [[-120, 0.1], [360, -0.45], [1500, -0.5], [3300, 0.0]]
  },
  "noise": { "TICKET_RATE": 0.08, "SENTIMENT": 0.03 },
  "faults": { "LAR_MULT": [[-120, 1.0]], "ORACLE_DEV": [[-120, 0.05]] },
  "flags": { "cannot_close": [] },
  "expected": [ { "t": 0, "LIQ_RATE": [100, 250] }, { "t": 840, "LIQ_RATE": [300, 550], "INS_FUND_PCT": [30, 50] } ]
}
```
- `PX` = cumulative fractional change of the scenario asset vs start; linear interpolation between keyframes.
- Any catalogue signal not listed in `tracks` sits at its baseline plus noise.
- `faults.LAR_MULT` multiplies *observed* liquidations only. This is how C3 (engine bug) makes LAR ≫ 1 with a small move.
- `expected` = tolerance bands used by tests only (no-operator-action run).

**Book (`book.py`).** Build the book once per scenario with `generate_portfolio(...)` at start prices. Each tick:
1. Price every asset from the scenario asset's move using `beta` (same mapping as `monte_carlo/engine.py`).
2. **Observed liquidations** = positions newly crossing `liq` since the last tick (sticky; a position liquidates once), × `book_scale` × `LAR_MULT`. `LIQ_RATE` = rolling 60 s count.
3. **Expected liquidations (LAR denominator):** precompute a lookup table `Δp ∈ [0, −20%] step 0.25% → share of open positions liquidated` from the same book (SPEC §9.2). `L_exp` = `n_open × (share(Δp_now) − share(Δp_60s_ago))`, per minute. `LAR = L_obs / max(L_exp, ε)`, smoothed over 60 s; LAR = 1.0 when both are below 1/min.
4. **Bad debt:** for each newly liquidated position, bankruptcy price = entry × (1 ∓ 1/lev). Shortfall = max(0, loss beyond margin) at the fill price, where fill = liq price moved further by `slippage × tick move`. The fund pays the shortfall. `BAD_DEBT_RATE` = %fund/min, `INS_FUND_PCT` = fund / start × 100. `ADL_COUNT` increments when the fund would go below 0 (the fund floors at 0).
5. `NEG_BAL_ACCTS` = count of liquidations with shortfall > 0 in the last 10 min (proxy).

Calibrate `book_scale`, `insurance_fund_usd` and `slippage` in C1 so the no-action run hits: LIQ_RATE crosses 100/min at about T+0, is 350–500/min around T+14, INS_FUND ≈ 40% at T+14, and falls through 25% around T+22–26 with no control. If pure book dynamics can't hit these, add an `INS_FUND_DRAIN` fault track, but keep LIQ_RATE and LAR book-driven (PLAN §3.5).

**Effects.** `SignalGenerator.step(t, effects: list[(Effect, approved_t)])` applies CONTRACTS §4 effects after generation, with linear ramp over `ramp_s`. Book-level knobs:
- `sim.new_exposure = 0` (reduce-only): stops the scripted PX track from deepening. Scale further negative moves by 0.4 from approval, since cascade selling is removed.
- `sim.liquidations_paused = 1`: observed liquidations are queued, not executed. On unpause they flush over 60 s, and shortfall grows with the move meanwhile (SPEC: pause is a trade-off).
- `sim.max_leverage` / `sim.maintenance_mult`: raise the liq buffer for not-yet-liquidated positions (use `MAINTENANCE_BUFFER` scaling).
- `sim.fund_topup_pct`: adds to the fund.

Document every knob in `SCHEMA.md`, because H3 references them.

**Signals (`signals.py`).** `SignalGenerator(scenario, seed)` with `.step(t, effects) -> SignalFrame` and `.reset()`. It computes PX_CHG_5M from the PX history. Noise uses `np.random.default_rng(seed + tick)` so any tick is reproducible regardless of call order.

## Tasks
- [ ] `clock.py` + tests (pause/resume/speed change/jump; no sleeping).
- [ ] `book.py` + tests: LAR ≈ 1.0 (0.7–1.5) on a pure market move; LAR > 3 with `LAR_MULT = 3.5`; the fund decreases monotonically without a top-up.
- [ ] `scenario_loader.py`: load and validate JSON (pydantic), interpolate tracks.
- [ ] `C1_black_tuesday.json` calibrated to SPEC §12.2 (T+0 warn, T+6 tickets 4×, T+14 critical, recovery from T+35, resolved by T+55 **if reduce-only is approved by T+18**).
- [ ] `signals.py` + `test_signals_c1.py`: `expected` bands pass on the no-action run; a second run with reduce-only effects at T+18 keeps INS_FUND > 30% and brings LIQ_RATE < 50/min by T+45.
- [ ] Performance: full 3600 s replay (1800 ticks) < 2 s on a laptop.

## Acceptance criteria
- Same seed → byte-identical frames (test).
- C1 no-action and C1 with-reduce-only runs meet the bands above.
- `SCHEMA.md` lets H8 write C2–C6 without reading the code.

## Out of scope
Severity, tags, state (H2); HTTP (H5).
