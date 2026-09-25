"""Deterministic signal generator (H1).

``SignalGenerator`` replays one scenario tick by tick (2 sim-seconds) and
returns a memoryless ``SignalFrame`` per tick:

- ``LIQ_RATE`` / ``LAR`` / ``BAD_DEBT_RATE`` / ``INS_FUND_PCT`` /
  ``ADL_COUNT`` / ``NEG_BAL_ACCTS`` come from the ``CrashBook`` (real
  position-level crossings).
- ``PX`` / ``PX_CHG_5M`` come from the scenario ``PX`` track (cumulative
  fractional change of the scenario asset) plus control dampening.
- Every other catalogue signal comes from its scripted track, or sits at
  its catalogue baseline plus seeded noise.

Determinism: noise uses ``np.random.default_rng`` seeded per (seed, tick,
signal) via a stable crc32 salt, so any tick is reproducible regardless of
call order. Same seed + same scenario + same effects ⇒ byte-identical
frames.
"""

from __future__ import annotations

from zlib import crc32

import numpy as np

from incident.catalogue import SIGNALS
from incident.contracts import Effect, SignalFrame
from simulation.market import ASSETS

from .book import CrashBook, lar_ratio
from .clock import TICK_S
from .scenario_loader import ScenarioLoader

BOOK_CODES = frozenset(
    {"LIQ_RATE", "LAR", "BAD_DEBT_RATE", "INS_FUND_PCT", "ADL_COUNT", "NEG_BAL_ACCTS"}
)
PX_CODES = frozenset({"PX", "PX_CHG_5M"})

FLAG_CODES = (
    "cannot_close",
    "wallet_compromise_suspected",
    "regulatory_notice",
    "partner_notice",
    "media_attention",
    "stablecoin_frozen_address",
)

_BASELINE = {s.code: s.baseline for s in SIGNALS}

# Effect signals understood as simulation knobs (CONTRACTS §4, SCHEMA.md).
KNOB_EXPOSURE = "sim.new_exposure"
KNOB_PAUSED = "sim.liquidations_paused"
KNOB_MAX_LEV = "sim.max_leverage"
KNOB_MAINT = "sim.maintenance_mult"
KNOB_TOPUP = "sim.fund_topup_pct"

#: Reduce-only dampening: further negative moves past the approval level are
#: scaled by this (cascade selling removed). See SCHEMA.md.
EXPOSURE_DAMPEN = 0.4


def _tick_index(t: int) -> int:
    return int(t // TICK_S)


class SignalGenerator:
    def __init__(self, scenario: ScenarioLoader, seed: int | None = None) -> None:
        self.scenario = scenario
        self.seed = scenario.spec.seed if seed is None else seed
        self.book = CrashBook(scenario)
        self._px_hist: list[tuple[int, float]] = []  # (t, px_eff)
        self._drop_hist: list[tuple[int, float]] = []  # (t, drawdown)
        self._last_px_eff = 0.0
        self._applied_topups: set[tuple[str, float, int]] = set()
        self._t = scenario.spec.preroll_s * -1

    # -- lifecycle ---------------------------------------------------------
    def reset(self) -> None:
        self.book.reset()
        self._px_hist.clear()
        self._drop_hist.clear()
        self._last_px_eff = 0.0
        self._applied_topups.clear()
        self._t = self.scenario.spec.preroll_s * -1

    # -- effects -------------------------------------------------------------
    @staticmethod
    def _ramp(t: int, approved_t: int, ramp_s: int) -> float:
        if t < approved_t:
            return 0.0
        if ramp_s <= 0:
            return 1.0
        return min(1.0, (t - approved_t) / ramp_s)

    def _resolve_knobs(
        self, t: int, effects: list[tuple[Effect, int]]
    ) -> tuple[float | None, bool, float, float | None]:
        """Return (exposure_approved_t|None, paused, maint_mult, max_lev)."""
        exposure_t: float | None = None
        paused = False
        maint = 1.0
        max_lev: float | None = None
        for eff, approved_t in effects:
            if t < approved_t:
                continue
            if eff.signal == KNOB_EXPOSURE and eff.value == 0:
                exposure_t = approved_t if exposure_t is None else min(exposure_t, approved_t)
            elif eff.signal == KNOB_PAUSED and eff.value >= 0.5:
                paused = True
            elif eff.signal == KNOB_MAINT:
                f = self._ramp(t, approved_t, eff.ramp_s)
                maint = 1.0 + (eff.value - 1.0) * f
            elif eff.signal == KNOB_MAX_LEV:
                if max_lev is None or eff.value < max_lev:
                    max_lev = float(eff.value)
            elif eff.signal == KNOB_TOPUP and eff.op == "add":
                key = (eff.signal, float(eff.value), int(approved_t))
                if key not in self._applied_topups:
                    self.book.add_topup_pct(float(eff.value))
                    self._applied_topups.add(key)
        return exposure_t, paused, maint, max_lev

    def _apply_signal_effects(
        self, code: str, value: float, t: int, effects: list[tuple[Effect, int]]
    ) -> float:
        for eff, approved_t in effects:
            if eff.signal != code:
                continue
            f = self._ramp(t, approved_t, eff.ramp_s)
            if f <= 0:
                continue
            if eff.op == "mult":
                value = value * (1.0 + (eff.value - 1.0) * f)
            elif eff.op == "add":
                value = value + eff.value * f
            elif eff.op == "cap":
                capped = min(value, eff.value)
                value = value + (capped - value) * f  # never raises
            elif eff.op == "set":
                value = value + (eff.value - value) * f
        return value

    # -- price path ----------------------------------------------------------
    def _px_raw(self, t: int) -> float:
        v = self.scenario.track_value("PX", t)
        return 0.0 if v is None else float(v)

    def _px_eff(self, t: int, px_raw: float, exposure_t: float | None) -> float:
        if exposure_t is None or t < exposure_t:
            return px_raw
        anchor = self._px_raw(exposure_t)
        if px_raw >= anchor:
            return px_raw  # recoveries pass through; only declines dampen
        return anchor + (px_raw - anchor) * EXPOSURE_DAMPEN

    def _px_at_or_before(self, t: int) -> float:
        if not self._px_hist:
            return 0.0
        best = self._px_hist[0][1]
        for ht, hv in self._px_hist:
            if ht <= t:
                best = hv
            else:
                break
        return best

    # -- main ------------------------------------------------------------------
    def step(self, t: int, effects: list[tuple[Effect, int]] | None = None) -> SignalFrame:
        effects = list(effects or [])
        spec = self.scenario.spec
        exposure_t, paused, maint, max_lev = self._resolve_knobs(t, effects)

        px_raw = self._px_raw(t)
        px_eff = self._px_eff(t, px_raw, exposure_t)
        tick_move = px_eff - self._last_px_eff
        self._last_px_eff = px_eff

        lar_mult = float(self.scenario.fault_value("LAR_MULT", t, 1.0))
        outcome = self.book.step(
            t, px_eff, tick_move,
            lar_mult=lar_mult, paused=paused,
            maintenance_mult=maint, max_leverage=max_lev,
        )

        # Optional scripted fund drain (SCHEMA.md). C1 does not use it; the
        # fund moves on book shortfall alone.
        drain = float(self.scenario.fault_value("INS_FUND_DRAIN", t, 0.0))
        if drain:
            dt = TICK_S
            self.book.fund_usd = max(
                0.0, self.book.fund_usd - self.book.start_fund * drain / 100.0 * dt / 60.0
            )

        self._px_hist.append((t, px_eff))
        drop_now = max(0.0, -px_eff)
        self._drop_hist.append((t, drop_now))

        l_obs = self.book.liq_rate(t)
        max_drop_win, start_drop = self._drop_window(t, 60)
        l_exp = self.book.expected_per_min(max_drop_win, start_drop)
        lar = lar_ratio(l_obs, l_exp)

        values: dict[str, float] = {}
        rng_tick = int(t // TICK_S)
        for sig in sorted(SIGNALS, key=lambda s: s.code):
            code = sig.code
            if code in BOOK_CODES or code in PX_CODES:
                continue
            track = self.scenario.track_value(code, t)
            base = float(track) if track is not None else float(sig.baseline)
            sigma = self.scenario.noise_sigma(code)
            if sigma:
                salt = crc32(f"{self.seed}:{rng_tick}:{code}".encode())
                rng = np.random.default_rng(salt)
                base = base + float(rng.normal(0.0, sigma))
            values[code] = self._apply_signal_effects(code, base, t, effects)

        # Book-driven signals (effects still apply on top, e.g. what-if caps).
        values["LIQ_RATE"] = self._apply_signal_effects("LIQ_RATE", l_obs, t, effects)
        values["LAR"] = lar
        values["BAD_DEBT_RATE"] = self.book.bad_debt_rate(t)
        values["INS_FUND_PCT"] = self.book.fund_pct
        values["ADL_COUNT"] = float(outcome.adl_count)
        values["NEG_BAL_ACCTS"] = self.book.neg_bal(t)

        # Price level + 5-minute change (percent).
        start = float(ASSETS[spec.asset]["start"]) if spec.asset in ASSETS else 100.0
        values["PX"] = start * (1.0 + px_eff)
        px_ago = self._px_at_or_before(t - 300)
        denom = start * (1.0 + px_ago)
        values["PX_CHG_5M"] = (values["PX"] - denom) / denom * 100.0 if denom else 0.0

        flags = {code: self.scenario.flag_active(code, t) for code in FLAG_CODES}
        meta = {
            "L_obs": float(l_obs),
            "L_exp": float(l_exp),
            "n_open": float(self.book.n_open),
            "fund_usd": float(self.book.fund_usd),
            "px_raw": float(px_raw),
            "px_eff": float(px_eff),
            "queued": float(outcome.queued),
            "lar_mult": float(lar_mult),
        }
        self._t = t
        return SignalFrame(t=t, values=values, flags=flags, meta=meta)

    def _drop_window(self, t: int, window_s: int) -> tuple[float, float]:
        """(max drawdown inside (t-window, t], drawdown at window start).

        The start value clamps to the earliest recorded drop when the
        lookback predates the replay, matching the event history's coverage.
        """
        start = self._drop_at_or_before(t - window_s)
        peak = start
        for ht, hv in self._drop_hist:
            if ht <= t - window_s:
                continue
            if ht > t:
                break
            peak = max(peak, hv)
        return peak, start

    def _drop_at_or_before(self, t: int) -> float:
        if not self._drop_hist:
            return 0.0
        best = self._drop_hist[0][1]
        for ht, hv in self._drop_hist:
            if ht <= t:
                best = hv
            else:
                break
        return best
