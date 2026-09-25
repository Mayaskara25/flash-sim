"""Book-driven liquidation dynamics (H1).

Reprices the existing synthetic book (``simulation/portfolio.py`` +
``liquidation/model.py``) along the scenario's price path to produce
``LIQ_RATE``, ``LAR``, ``BAD_DEBT_RATE``, ``INS_FUND_PCT``, ``ADL_COUNT``
and ``NEG_BAL_ACCTS``. This is what makes the tool MochaTrade-specific
(PLAN §3.5): liquidations come from real position-level crossings, not from
a scripted curve.

Liquidation economics (incident model — deliberately NOT the repo's
research ``MAINTENANCE_BUFFER``):
- A position liquidates at ``entry × (1 ∓ INCIDENT_BUFFER/lev)`` with
  ``INCIDENT_BUFFER = 0.8 < 1``: liquidation fires *before* the trader's
  margin is wiped out, so an orderly liquidation leaves **no shortfall**.
- Shortfall (bad debt, paid by the fund) appears only when the fill slips
  or gaps past the wipe-out point (``1.0/lev``): ``fill = liq`` moved
  further adverse by ``slippage × |cumulative drawdown|`` — an *execution
  depth* factor, not a fee or an instantaneous-tick multiplier. The market
  gets thinner the deeper a crash goes (liquidity is consumed by the
  cascade itself), so fills slip further behind the trigger price the
  deeper the book has already fallen, regardless of any one tick's local
  slope. This was previously modelled as ``slippage × |tick move|``
  (an instantaneous 2 s delta extrapolated by a ~40-tick multiplier), which
  spiked bad debt into a one-tick cliff whenever a scripted PX segment
  was briefly steeper than its neighbours — the cliff tracked the price
  *script's* local slope, not the crash's actual depth. Depth-based slip
  keeps shortfall a smooth, monotonic function of how far the crash has
  gone, so gentle early phases produce liquidations with little or no
  shortfall and the drain accelerates as the crash deepens (SPEC's M2
  "waterfall" narrative) instead of jumping in a single tick.
  ``NEG_BAL_ACCTS`` counts only shortfall-carrying liquidations in the
  last 10 min (a real count, not a proxy).

Conventions (all per the H1 handoff):
- The book is built once per scenario with ``generate_portfolio`` at start
  prices. Positions already past their threshold at build ("underwater at
  the start", entry-spread outliers) are dropped silently. Liquidation is
  sticky: a position liquidates once.
- Observed liquidations = newly crossed positions × ``book_scale`` ×
  ``LAR_MULT`` (the ``faults.LAR_MULT`` track; how C3 makes LAR ≫ 1).
- Expected liquidations come from a precomputed lookup table
  ``Δp ∈ [0, −20%] step 0.25% → share of open positions liquidated``
  (SPEC §9.2), evaluated as the trailing-60 s window maximum drawdown
  (see ``expected_per_min``).
- ``ADL_COUNT`` increments when the fund would go below 0 (fund floors at 0).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from simulation.market import ASSETS
from simulation.portfolio import generate_portfolio

from .scenario_loader import ScenarioLoader

#: Incident liquidation buffer (fraction of initial margin consumed before
#: the modelled liquidation). 0.8 < 1: liquidation precedes margin wipe-out,
#: so only gap/slip past 1.0/lev creates bad debt. The repo's research
#: MAINTENANCE_BUFFER (1.55) would put every liquidation underwater from the
#: first tick and escalate a calm market — it is intentionally not used here.
INCIDENT_BUFFER = 0.8

LAR_GRID_MAX = 0.20
LAR_GRID_STEP = 0.0025
ROLL_LIQ_S = 60
ROLL_NEG_S = 600
#: Noise floor for the LAR denominator (liquidations/min). Below ~2 expected
#: liquidations/min, single-position lumpiness dominates the book tail, so an
#: unguarded ratio reports phantom anomalies. Genuine faults (LAR_MULT ≥ 2
#: with real volume) are far above this floor and unaffected.
LAR_EPS = 2.0
#: Minimum observed liquidations/min for a meaningful classification. Below
#: this, count noise dominates (a 6-vs-2 split is luck, not a diagnosis), so
#: LAR reports 1.0 rather than a spurious spike — including the first
#: crossings of a replay while the rolling windows fill.
LAR_MIN_COUNT = 10.0


def lar_ratio(l_obs: float, l_exp: float) -> float:
    """Liquidation anomaly ratio with noise guards (SPEC §9.2)."""
    if l_obs < LAR_MIN_COUNT:
        return 1.0
    return float(l_obs) / max(float(l_exp), LAR_EPS)


@dataclass
class LiqOutcome:
    t: int
    n_new_raw: int
    n_new_scaled: float
    shortfall_usd: float
    fund_usd: float
    fund_pct: float
    adl_count: int
    queued: int


class CrashBook:
    """Sticky-liquidation book repriced along a scenario price path."""

    def __init__(self, scenario: ScenarioLoader) -> None:
        spec = scenario.spec
        self.scenario_id = spec.id
        self.asset = spec.asset
        self.book_scale = float(spec.book.book_scale)
        self.slippage = float(spec.book.slippage)
        self.start_fund = float(spec.book.insurance_fund_usd)
        self.fund_usd = float(spec.book.insurance_fund_usd)
        self.adl_count = 0

        start_prices = {s: m["start"] for s, m in ASSETS.items()}
        pf = generate_portfolio(
            n_traders=spec.book.n_traders,
            avg_leverage=spec.book.avg_leverage,
            long_ratio=spec.book.long_ratio,
            prices=start_prices,
            seed=spec.seed,
        )
        self.n_total = len(pf["entry"])
        self.entry = np.asarray(pf["entry"], dtype=float)
        self.qty = np.asarray(pf["qty"], dtype=float)
        self.lev = np.asarray(pf["leverage"], dtype=float)
        self.is_long = np.asarray(pf["is_long"], dtype=bool)
        self.margin = self.entry * self.qty / self.lev
        assets = np.asarray(pf["asset"])
        self.betas = np.array([ASSETS[a]["beta"] for a in assets], dtype=float)
        self.starts = np.array([ASSETS[a]["start"] for a in assets], dtype=float)

        self.liquidated = np.zeros(self.n_total, dtype=bool)
        self.n_short_liq = 0
        # Cold start: positions already past their threshold at the build
        # price (entry-spread outliers) are marked liquidated silently — no
        # events, no fund impact. Otherwise they all "liquidate" in tick 1
        # while L_exp ≈ 0 and LAR spikes to absurd values.
        self._mark_cold_start()
        # Event log: (t, scaled_count, scaled_shortfall, scaled_neg_count).
        # neg counts only liquidations whose shortfall > 0 (NEG_BAL_ACCTS);
        # with INCIDENT_BUFFER < 1 most liquidations carry no shortfall.
        self.events: list[tuple[int, float, float, float]] = []
        self.queue: list[int] = []  # paused-liquidation backlog (raw indices)

        self._lookup_grid = np.arange(0.0, LAR_GRID_MAX + LAR_GRID_STEP / 2, LAR_GRID_STEP)
        self._lookup_share = self._build_lookup()
        # Exact per-position crossing drops for the LAR denominator (see
        # expected_per_min): grid interpolation error dominates the sparse
        # tail (first tenths of a percent), phantom-raising LAR at crash
        # onset. d_i = NVDA drawdown at which a LONG crosses its base
        # threshold (px_chg <= (liq/start - 1)/beta, i.e. drop >= d_i).
        # Shorts are excluded: their crossed-set SHRINKS as drops grow
        # (they uncross while falling), which made exact counts non-monotonic
        # and undercounted the denominator. Intra-window short crossings on
        # rallies are not modelled — our scenarios never rally above start
        # (C1 has zero short crossings; asserted in test_signals_c1).
        base_liq = self._liq_thresholds()
        with np.errstate(divide="ignore", invalid="ignore"):
            move = (base_liq / self.starts - 1.0) / self.betas
        self._long_d = np.sort(-move[self.is_long])

    # -- setup -----------------------------------------------------------
    def _liq_thresholds(
        self, maintenance_mult: float = 1.0, max_leverage: float | None = None
    ) -> np.ndarray:
        lev = self.lev
        if max_leverage is not None:
            lev = np.minimum(lev, max_leverage)
        move = (INCIDENT_BUFFER * maintenance_mult) / lev
        return np.where(self.is_long, self.entry * (1.0 - move), self.entry * (1.0 + move))

    def _build_lookup(self) -> np.ndarray:
        """Share of the book liquidated at each grid drawdown (base knobs)."""
        base_liq = self._liq_thresholds()
        shares = np.zeros_like(self._lookup_grid)
        for i, drop in enumerate(self._lookup_grid):
            px = self.starts * (1.0 - drop * self.betas)
            crossed = np.where(self.is_long, px <= base_liq, px >= base_liq)
            shares[i] = crossed.mean()
        # Monotonic non-decreasing guard against float noise.
        return np.maximum.accumulate(shares)

    def lookup_share(self, drop: float) -> float:
        """Expected cumulative liquidated share at NVDA drawdown ``drop``.

        Linearly interpolated between grid points so sub-step moves yield
        small-but-nonzero expectations (a step function would report
        ``L_exp = 0`` for tiny moves and blow LAR up to absurd values).
        """
        drop = min(max(float(drop), 0.0), LAR_GRID_MAX)
        pos = drop / LAR_GRID_STEP
        lo = min(int(pos), len(self._lookup_share) - 2)
        frac = pos - lo
        return float(self._lookup_share[lo] * (1.0 - frac) + self._lookup_share[lo + 1] * frac)

    def _mark_cold_start(self) -> None:
        px0 = self.starts  # px_chg = 0
        liq0 = self._liq_thresholds()
        cold = np.where(self.is_long, px0 <= liq0, px0 >= liq0)
        self.liquidated[cold] = True
        self.n_liquidated_raw = int(cold.sum())

    # -- per-tick ----------------------------------------------------------
    def current_prices(self, px_chg: float) -> np.ndarray:
        return self.starts * (1.0 + float(px_chg) * self.betas)

    def _shortfall(self, idx: np.ndarray, liq: np.ndarray, px_chg: float) -> np.ndarray:
        """Shortfall for newly-liquidated positions ``idx``.

        ``slip`` scales with the crash's *cumulative* depth (``px_chg``,
        the scenario asset's fractional move since start), not with any
        single tick's instantaneous move — see the module docstring for why
        (a depth-based, path-independent slip is what keeps bad debt a
        smooth function of the crash rather than a one-tick cliff).
        """
        slip = self.slippage * abs(float(px_chg))
        fill = np.where(self.is_long[idx], liq[idx] * (1.0 - slip), liq[idx] * (1.0 + slip))
        loss = np.where(
            self.is_long[idx],
            (self.entry[idx] - fill) * self.qty[idx],
            (fill - self.entry[idx]) * self.qty[idx],
        )
        return np.maximum(0.0, loss - self.margin[idx])

    def step(
        self,
        t: int,
        px_chg: float,
        tick_move: float = 0.0,
        lar_mult: float = 1.0,
        paused: bool = False,
        maintenance_mult: float = 1.0,
        max_leverage: float | None = None,
    ) -> LiqOutcome:
        # `tick_move` (the single-tick price delta) is accepted for call-site
        # compatibility but no longer used: shortfall is driven by the
        # crash's cumulative depth (`px_chg`), not the local tick slope
        # (see `_shortfall`).
        liq = self._liq_thresholds(maintenance_mult, max_leverage)
        px = self.current_prices(px_chg)
        survivors = ~self.liquidated
        crossed = np.where(self.is_long, px <= liq, px >= liq) & survivors
        new_idx = np.flatnonzero(crossed)

        if paused:
            # Queue, don't execute. Shortfall is realised at flush time at
            # the then-current (worse) prices — the SPEC trade-off of pausing.
            self.queue.extend(new_idx.tolist())
            self.liquidated[new_idx] = True  # sticky: never double-count
            self.events.append((t, 0.0, 0.0, 0.0))
            return LiqOutcome(t, 0, 0.0, 0.0, self.fund_usd, self.fund_pct, self.adl_count, len(self.queue))

        # Flush backlog gradually (over ~60 s) when unpaused.
        if self.queue:
            release = max(1, len(self.queue) // 30)
            flush_idx = np.array(self.queue[:release], dtype=int)
            self.queue = self.queue[release:]
            new_idx = np.concatenate([new_idx, flush_idx]) if len(new_idx) else flush_idx

        self.liquidated[new_idx] = True
        self.n_liquidated_raw += len(new_idx)
        if len(new_idx):
            self.n_short_liq += int((~self.is_long[new_idx]).sum())
        per_pos = self._shortfall(new_idx, liq, px_chg) if len(new_idx) else np.zeros(0)
        raw_shortfall = float(per_pos.sum())
        raw_neg = int((per_pos > 0).sum())
        scale = self.book_scale * float(lar_mult)
        scaled_n = float(len(new_idx)) * scale
        scaled_shortfall = raw_shortfall * scale
        scaled_neg = float(raw_neg) * scale

        if scaled_shortfall > 0 and self.fund_usd <= 0:
            # Fund already empty: every further shortfall is an ADL event.
            self.adl_count += int(round(scaled_n)) if scaled_n else 1
        elif scaled_shortfall >= self.fund_usd and scaled_shortfall > 0:
            self.adl_count += 1
        self.fund_usd = max(0.0, self.fund_usd - scaled_shortfall)
        self.events.append((t, scaled_n, scaled_shortfall, scaled_neg))
        return LiqOutcome(
            t, len(new_idx), scaled_n, scaled_shortfall,
            self.fund_usd, self.fund_pct, self.adl_count, len(self.queue),
        )

    # -- derived -----------------------------------------------------------
    @property
    def fund_pct(self) -> float:
        return 100.0 * self.fund_usd / self.start_fund if self.start_fund else 0.0

    @property
    def n_open(self) -> int:
        return int(self.n_total - self.n_liquidated_raw)

    def add_topup_pct(self, pct: float) -> float:
        self.fund_usd += self.start_fund * float(pct) / 100.0
        return self.fund_usd

    def rolling(self, t: int, window_s: int) -> tuple[float, float, float]:
        """(scaled count, scaled shortfall, scaled neg count) in ``(t-window, t]``."""
        c, s, n = 0.0, 0.0, 0.0
        lo = t - window_s
        for et, ec, es, en in reversed(self.events):
            if et <= lo:
                break
            c += ec
            s += es
            n += en
        return c, s, n

    def liq_rate(self, t: int) -> float:
        c, _, _ = self.rolling(t, ROLL_LIQ_S)
        return float(c)  # 60 s window ⇒ count == per-minute rate

    def bad_debt_rate(self, t: int) -> float:
        _, s, _ = self.rolling(t, ROLL_LIQ_S)
        return 100.0 * s / self.start_fund if self.start_fund else 0.0

    def neg_bal(self, t: int) -> float:
        _, _, n = self.rolling(t, ROLL_NEG_S)
        return float(n)

    def _long_crossed(self, drop: float) -> int:
        """Long positions with base crossing drop <= ``drop`` (exact)."""
        return int(np.searchsorted(self._long_d, drop, side="right"))

    def expected_per_min(self, max_drop_win: float, start_drop: float) -> float:
        # Exact long-threshold counting (not the gridded table): the longs
        # crossing in a window are precisely those whose crossing drop lies
        # in (start_drop, max_drop_win]. SPEC §9.2's lookup table
        # (``lookup_share``, kept as the published artifact and for coarse
        # queries) approximates this; grid interpolation error in the sparse
        # tail phantom-raised LAR at crash onset, so the denominator counts
        # exactly. (SPEC writes N_open; the increment over the initial book
        # is the quantity matching observed sticky crossings.)
        #
        # The window's *maximum* drawdown (not the instantaneous drop) is
        # used so the expectation covers the same trailing 60 s the observed
        # rolling count does. An instantaneous diff collapses to 0 the moment
        # price bottoms while the rolling count still holds trough crossings,
        # phantom-spiking LAR on every recovery onset.
        #
        # Intra-window short crossings on rallies are not modelled (our
        # scenarios never rally above start; C1 has zero short crossings —
        # asserted in test_signals_c1).
        n = self._long_crossed(max_drop_win) - self._long_crossed(start_drop)
        return float(max(n, 0)) * self.book_scale

    def reset(self) -> None:
        self.liquidated[:] = False
        self.n_short_liq = 0
        self._mark_cold_start()
        self.fund_usd = self.start_fund
        self.adl_count = 0
        self.events.clear()
        self.queue.clear()
