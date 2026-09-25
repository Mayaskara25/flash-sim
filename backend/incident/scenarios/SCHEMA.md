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
  Keep the pre-roll **flat** (repeat the opening value, e.g.
  `[[-120, 0], [0, 0], …]`): any pre-roll ramp generates liquidations before
  T+0 and escalates a calm market.
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
| `insurance_fund_usd` | 135000.0 | Starting fund. Calibrated so C1 no-action crosses 25% at ~T+24 while the reduce-only branch stays above 60% (H2's resolve needs fund above warn) |
| `slippage` | 40.0 | **Execution-gap factor**, not a fee: fill trails the market by this many ticks' worth of movement (`fill = liq` moved adverse by `slippage × |tick move|`). Tens of ticks: liquidations execute minutes behind in a cascading market. Gentle phases produce zero shortfall (headroom `0.2/lev` covers the slip); steep phases produce bad debt. This decoupling lets LIQ_RATE (counts) and fund drain (steepness) calibrate independently |

Liquidation math (see `book.py`): sticky crossings of
`liq = entry × (1 ∓ 0.8/lev)` (`INCIDENT_BUFFER = 0.8 < 1`, deliberately not
the repo research buffer 1.55 — orderly liquidations leave no shortfall, so a
calm market never escalates); `LIQ_RATE` = rolling-60 s scaled count
(= per-minute rate); `L_exp` = exact count of long thresholds in the
trailing-60 s (window-start, window-max-drawdown] interval (SPEC §9.2's
Δp → share table is kept as the published artifact and for coarse queries;
the denominator counts exactly because grid interpolation error dominated the
sparse tail). `LAR = L_obs / L_exp` (1.0 below counting significance —
fewer than 10 observed liquidations/min; denominator floored at 2/min
against book-tail lumpiness). The window **maximum** drawdown (not the
instantaneous drop) is used so the expectation covers the same trailing 60 s
the rolling observed count does — an instantaneous diff phantom-spikes LAR on
every recovery onset. `BAD_DEBT_RATE` = rolling-60 s shortfall as % of start
fund; `ADL_COUNT` increments when shortfall would push the fund below 0
(fund floors at 0); `NEG_BAL_ACCTS` = rolling-10-min liquidations with
shortfall > 0 (a real count: most liquidations carry none).

Known limitation: unpausing a liquidation pause flushes the backlog while the
price-based expectation is ~0, spiking LAR. C1 never pauses; H8 pause
scenarios should expect it (flushed liquidations are real, just deferred).

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
| `sim.maintenance_mult = m` (set) | Buffer `0.8` → `0.8 × m` for survivors (`m > 1` delays liquidation; ramps linearly). Never creates bad debt by itself (stays below 1.0 for sane `m`) |
| `sim.fund_topup_pct = p` (add) | `fund += p%` of start fund, applied once per approval |
| `<CODE>` mult/add/cap/set | Generic post-generation tweak of any signal value (e.g. what-if caps). `cap` never raises. Note H3's `reduce_only` pairs `sim.new_exposure` with `LIQ_RATE mult 0.6` — the mult trims displayed LIQ only; fund relief comes from the dampened price path |

## C1 calibration reference (tolerances, no-action run, seed 42)

- Pre-roll (T−120…T+0): dead calm — `LIQ_RATE`/`BAD_DEBT_RATE`/`NEG_BAL_ACCTS`
  all 0, fund 100%, every signal normal (H2 stays NORMAL).
- T+0: crash starts (flat pre-roll before it). `LIQ_RATE` crosses 100/min
  ~T+3 (WARNING), 300/min ~T+13 (CRITICAL, 336/min at T+14 with fund intact).
- T+6: `TICKET_RATE` ≈ 4× (I1). LAR stays 0.7–1.5 throughout (market-driven;
  exactly 1.00 at most markers — the denominator counts thresholds exactly).
- No-action: waterfall T+20–26 drains the fund through 25% at ~T+24
  (SEV-1 branch, stays EMERGENCY — the fund never recovers). Reduce-only
  (H3 effects) approved at T+18: dampened ticks fall below the shortfall
  headroom, fund stays at ~100%, all signals below warn from ~T+35, so H2
  proposes resolve after 15 min and IC confirmation resolves ~T+50.
- Full 3600 s replay (1861 ticks) runs in < 2 s (vectorised numpy, 10k book).
