# Scenario pack schema (H1) — how to write C2–C6 without reading the code

This is the contract H8 builds on. A scenario is a single JSON file in
`backend/incident/scenarios/`. The filename is free (`C1_black_tuesday.json`);
the session resolves scenarios by the **`id` field**, not the filename.

All times are **sim-seconds** (`t`, int; `t = 0` is scenario T+0, negative is
pre-roll). One tick = 2 sim-seconds. Values between keyframes are **linearly
interpolated**; outside the keyframe range the edge value holds (clamped).

## Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `id` | `"C1"`…`"C6"` | Scenario id, must be unique |
| `name` / `description` | str | Shown in `GET /incident/scenarios` |
| `preroll_s` | int (120) | Seconds of baseline simulated before T+0 |
| `duration_s` | int (3600) | Scenario length; H5 stops the clock here |
| `seed` | int (42) | Seeds the book build and all signal noise |
| `asset` | `"NVDA"` | Scenario asset; other assets follow via `beta` (same mapping as `monte_carlo/engine.py`: `px_asset = start × (1 + chg × beta)`) |
| `book` | object | Book calibration (below) |
| `tracks` | `{code: [[t, v], …]}` | Scripted signal paths (below) |
| `noise` | `{code: sigma}` | Per-tick Gaussian σ added on top of scripted/baseline values |
| `faults` | `{code: [[t, v], …]}` | Fault multipliers (below) |
| `flags` | `{code: [[t_start, t_end], …]}` | Boolean-window flags (`cannot_close`, `wallet_compromise_suspected`, `regulatory_notice`, `partner_notice`, `media_attention`, `stablecoin_frozen_address`) |
| `expected` | `[{t, CODE: [lo, hi], …}]` | **Tests only.** Tolerance bands for the no-operator-action run, checked by `test_signals_c1.py` (and H8's golden tests) |

## `tracks`

- `PX` — **cumulative fractional change** of the scenario asset vs its start
  (e.g. `-0.06` = −6%). Required; drives the book, `PX` and `PX_CHG_5M`.
- Any other catalogue code (`TICKET_RATE`, `SENTIMENT`, `STBL_PX`,
  `ORACLE_DEV`, …) — scripted path for that signal.
- Any catalogue code **not** listed sits at its catalogue baseline plus noise.

## `book`

| Field | C1 value | Meaning |
|---|---|---|
| `n_traders` | 10000 | Synthetic leveraged positions |
| `avg_leverage` | 14.7 | Center of the leverage-bucket distribution |
| `long_ratio` | 0.72 | Share of longs (crash hurts longs) |
| `book_scale` | 1.0 | Multiplies observed liquidations **and** expected ones, so LAR is scale-invariant. Keep 1.0: raising it breaks LAR ≈ 1 on market moves |
| `insurance_fund_usd` | 4080000.0 | Starting fund. Calibrated so C1 no-action sits at ~38% at T+14 and crosses 25% at ~T+24 |
| `slippage` | 0.35 | Fill = liq price moved further adverse by `slippage × |tick move|`; shortfall = `max(0, loss beyond margin)` at the fill, paid by the fund |

Liquidation math (see `book.py`): sticky crossings of
`liq = entry × (1 ∓ 1.55/lev)`; `LIQ_RATE` = rolling-60 s scaled count
(= per-minute rate); `L_exp = N_initial × (share(Δp_now) − share(Δp_60s_ago))`
from the precomputed Δp → liquidated-share table (SPEC §9.2; `N_initial`
because table shares are cumulative over the original book);
`LAR = L_obs / L_exp` (1.0 below counting significance — fewer than 5 observed
liquidations/min — or when both are below 1/min; denominator floored at 2/min
against book-tail lumpiness). `L_exp` uses the trailing-60 s **maximum**
drawdown so it covers the same window the rolling observed count does (an
instantaneous diff would phantom-spike LAR on every recovery onset);
shortfall as % of start fund; `ADL_COUNT` increments when shortfall would
push the fund below 0 (fund floors at 0); `NEG_BAL_ACCTS` = rolling-10-min
liquidations with shortfall > 0 (every liquidation carries shortfall here,
so it is a proxy — per the H1 handoff).

## `faults`

| Track | Default | Meaning |
|---|---|---|
| `LAR_MULT` | 1.0 | Multiplies **observed** liquidations only. C3's engine bug sets ~3.5 with a small price move → LAR ≫ 1 while `L_exp` stays put |
| `ORACLE_DEV` | — | Scripted oracle deviation (no book interaction) |
| `INS_FUND_DRAIN` | 0.0 | Extra fund drain in **%fund/min** (e.g. `[[840, 0.5]]`). Escape hatch if book dynamics alone cannot hit a fund target — C1 does **not** use it; `LIQ_RATE`/`LAR` stay book-driven |

## Control-effect knobs (`sim.*` effect signals, CONTRACTS §4)

Applied by `SignalGenerator.step` **after** generation, with linear ramp over
`ramp_s` for value effects. Threshold knobs (`new_exposure`, `paused`,
`max_leverage`, `topup`) apply in full from `approved_t`.

| Knob effect | Semantics |
|---|---|
| `sim.new_exposure = 0` (set) | Reduce-only: further **declines** past the approval-level price are scaled × **0.4** (cascade selling removed); recoveries pass through |
| `sim.liquidations_paused = 1` (set) | Crossings are **queued**, not executed (`LIQ_RATE` reads 0 meanwhile). On unpause the queue flushes over ~60 s and shortfall is computed at the then-current (worse) prices — pausing is a trade-off (SPEC §9.4) |
| `sim.max_leverage = X` (set) | Survivors' thresholds recomputed with `lev := min(lev, X)` (wider buffer, fewer new liquidations) |
| `sim.maintenance_mult = m` (set) | Buffer `1.55` → `1.55 × m` for survivors (`m > 1` delays liquidation; ramps linearly) |
| `sim.fund_topup_pct = p` (add) | `fund += p%` of start fund, applied once per approval |
| `<CODE>` mult/add/cap/set | Generic post-generation tweak of any signal value (e.g. what-if caps). `cap` never raises |

## C1 calibration reference (tolerances, no-action run, seed 42)

- T−60: `LIQ_RATE` 5–80 (cascade starting); T+0: `LIQ_RATE` 300–550
  (crosses 100/min during the opening minute), `PX_CHG_5M` = −6% (warn).
- T+6: `TICKET_RATE` ≈ 4× (I1). T+14: `LIQ_RATE` 300–550, `INS_FUND_PCT`
  30–50 (≈38%). LAR stays 0.7–1.5 throughout the crash (market-driven).
- No-action: fund crosses 25% at ~T+24 (SEV-1 branch). Reduce-only approved
  at T+18: fund never drops below 30%, `LIQ_RATE` < 50/min by T+45, full
  recovery by T+55.
- Full 3600 s replay (1860 ticks) runs in < 2 s (vectorised numpy, 10k book).
