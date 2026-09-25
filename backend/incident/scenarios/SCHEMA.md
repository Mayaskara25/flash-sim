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
  Keep the pre-roll **flat until the last ~30 s** (repeat the opening value,
  e.g. `[[-120, 0], [-30, 0], [0, -0.006], …]`): a ramp that starts much
  earlier than that generates enough liquidations before T+0 to escalate a
  calm market past watch (C1's own T-0:30 kick-off is small enough that
  every pre-roll signal still stays at watch or below through T+0).
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
| `insurance_fund_usd` | 135000.0 | Starting fund. Calibrated so C1 no-action crosses 25% between T+20 and T+26 while the reduce-only branch never drops below 25% (floors around 34%) |
| `slippage` | 0.207 | **Execution-depth factor**, not a fee or a per-tick multiplier: `fill = liq` moved adverse by `slippage × |cumulative drawdown|` (the scenario asset's fractional move since start, not any single tick's delta). The book gets thinner the deeper a crash goes, so fills slip further behind the trigger price the deeper the crash currently is. Gentle/shallow phases produce zero shortfall (headroom `0.2/lev` covers the slip until depth passes roughly `0.2/(lev × slippage)`); the drain accelerates smoothly as the crash deepens. This was previously `slippage × |tick move|` (an instantaneous 2 s delta extrapolated by a large tick-count multiplier); that model spiked bad debt into a one-tick cliff whenever a scripted PX segment was briefly steeper than its neighbours, because it tracked the price *script's* local slope rather than the crash's actual depth |

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
fund, driven by the depth-based slip above so it turns on gradually as the
crash deepens rather than jumping in a single tick; `ADL_COUNT` increments
when shortfall would push the fund below 0 (fund floors at 0);
`NEG_BAL_ACCTS` = rolling-10-min liquidations with shortfall > 0 (a real
count: most liquidations carry none).

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
| `sim.new_exposure = 0` (set) | Reduce-only: further **declines** past the approval-level price are scaled × **0.1** (`EXPOSURE_DAMPEN` in `signals.py` — cascade selling removed); recoveries pass through. With depth-based shortfall, the approval point is often already past the fund's danger depth, so the dampening has to nearly halt further decline (not just slow it) for reduce-only to actually hold the fund above 25% |
| `sim.liquidations_paused = 1` (set) | Crossings are **queued**, not executed (`LIQ_RATE` reads 0 meanwhile). On unpause the queue flushes over ~60 s and shortfall is computed at the then-current (worse) prices — pausing is a trade-off (SPEC §9.4) |
| `sim.max_leverage = X` (set) | Survivors' thresholds recomputed with `lev := min(lev, X)` (wider buffer, fewer new liquidations) |
| `sim.maintenance_mult = m` (set) | Buffer `0.8` → `0.8 × m` for survivors (`m > 1` delays liquidation; ramps linearly). Never creates bad debt by itself (stays below 1.0 for sane `m`) |
| `sim.fund_topup_pct = p` (add) | `fund += p%` of start fund, applied once per approval |
| `<CODE>` mult/add/cap/set | Generic post-generation tweak of any signal value (e.g. what-if caps). `cap` never raises. Note H3's `reduce_only` pairs `sim.new_exposure` with `LIQ_RATE mult 0.6` — the mult trims displayed LIQ only; fund relief comes from the dampened price path |

## C1 calibration reference (tolerances, no-action run, seed 42)

- Pre-roll (T−2:00…T−0:30): dead calm — `LIQ_RATE`/`BAD_DEBT_RATE`/
  `NEG_BAL_ACCTS` all 0, fund 100%, every signal normal. From T−0:30 PX
  starts falling (by design), so a handful of liquidations trickle in
  before T+0, but every signal stays at watch or below through T+0
  (H2 stays NORMAL/WATCH).
- T+0..T+3: `LIQ_RATE` crosses 100/min by T+2; `PX_CHG_5M` reaches -5%
  (WARNING) within T+0..T+3.
- T+6: `TICKET_RATE` ≈ 4× (I1); fund ≈ 90-99% (gradual drain has started,
  `BAD_DEBT_RATE` > 0 from ~T+3, not a cliff).
- T+14: `LIQ_RATE` 350-500/min (CRITICAL), fund drained to ~35-45%. LAR
  stays 0.7-1.5 throughout (market-driven; exactly 1.00 at most markers —
  the denominator counts thresholds exactly).
- No-action: waterfall T+20-26 drains the fund through 25% (SEV-1 branch
  via the fund hard override; the fund does not recover on its own).
  Reduce-only (H3 effects) approved at T+18: the depth-based shortfall
  model means T+18 is often already past the fund's danger depth, so the
  dampening (`EXPOSURE_DAMPEN = 0.1`) has to nearly halt further decline;
  the fund floors around 34% (never below 25%), `LIQ_RATE` < 50/min well
  before T+45, all signals but `INS_FUND_PCT` clear below warn from ~T+35
  (`INS_FUND_PCT` itself settles below the 60% warn line without a top-up —
  H2's resolve rule special-cases it, PLAN §3 decision #13), so H2 proposes
  resolve after 15 min of that and IC confirmation resolves by ~T+58.
- Full 3600 s replay (1861 ticks) runs in < 2 s (vectorised numpy, 10k book).
