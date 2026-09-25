"""Severity score + hard overrides (H2, SPEC §3)."""

from __future__ import annotations

import pytest

from incident.catalogue import SIGNALS, status_of
from incident.contracts import SignalFrame
from incident.rules.history import SignalHistory
from incident.rules.severity import SeverityResult, score

_BY_CODE = {s.code: s for s in SIGNALS}

ALL_FLAGS = (
    "cannot_close",
    "wallet_compromise_suspected",
    "regulatory_notice",
    "partner_notice",
    "media_attention",
    "stablecoin_frozen_address",
)


def make_frame(
    values: dict[str, float] | None = None, flags: dict[str, bool] | None = None, t: int = 0
) -> SignalFrame:
    base = {s.code: float(s.baseline) for s in SIGNALS}
    base.update(values or {})
    full_flags = {code: False for code in ALL_FLAGS}
    full_flags.update(flags or {})
    return SignalFrame(t=t, values=base, flags=full_flags, meta={})


def empty_history() -> SignalHistory:
    return SignalHistory()


# -- CONTRACTS §2 threshold table -------------------------------------------

def _probe(code: str, level: str) -> float:
    """A value just inside `level` for signal `code`."""
    sig = _BY_CODE[code]
    thr = {"watch": sig.watch, "warn": sig.warn, "critical": sig.critical}[level]
    assert thr is not None
    if sig.direction == "up":
        return float(thr)
    return float(thr)


def _below_watch(code: str) -> float:
    sig = _BY_CODE[code]
    if sig.direction == "up":
        return float(sig.baseline)
    # direction down: baseline is the healthy (high) side; use baseline.
    return float(sig.baseline)


@pytest.mark.parametrize("sig", SIGNALS, ids=[s.code for s in SIGNALS])
def test_threshold_table_below_at_above(sig) -> None:
    # Baseline side is always normal.
    assert status_of(sig.code, _below_watch(sig.code)) == "normal"
    for level in ("watch", "warn", "critical"):
        thr = {"watch": sig.watch, "warn": sig.warn, "critical": sig.critical}[level]
        if thr is None:
            continue  # skipped level never matches (H0 rule)
        expected = level
        if level == "watch" and sig.watch == sig.warn:
            # Degenerate catalogue row (BAD_DEBT_RATE: watch == warn):
            # the exact threshold reads as warn since warn is checked first.
            expected = "warn"
        assert status_of(sig.code, _probe(sig.code, level)) == expected


def test_none_thresholds_never_match() -> None:
    # ADL_COUNT has no watch/warn; NEG_BAL_ACCTS has no watch.
    assert status_of("ADL_COUNT", 0) == "normal"
    assert status_of("ADL_COUNT", 1) == "critical"
    assert status_of("NEG_BAL_ACCTS", 0) == "normal"
    assert status_of("NEG_BAL_ACCTS", 1) == "warn"


# -- dimensions ---------------------------------------------------------------

def test_all_baseline_scores_zero() -> None:
    res = score(make_frame(), empty_history(), "NONE")
    assert res.score == 0.0
    assert all(v == 0.0 for v in res.dims.values())
    assert res.overrides == []


def test_f_ignores_lar_when_market_but_counts_when_system() -> None:
    market = score(make_frame({"LAR": 3.5}), empty_history(), "MARKET")
    assert market.dims["F"] == 0.0
    system = score(make_frame({"LAR": 3.5}), empty_history(), "SYSTEM")
    assert system.dims["F"] == 5.0


def test_b_fund_curve_and_bad_debt_floor() -> None:
    assert score(make_frame({"INS_FUND_PCT": 100.0}), empty_history(), "NONE").dims["B"] == 0.0
    assert score(make_frame({"INS_FUND_PCT": 50.0}), empty_history(), "NONE").dims["B"] == 5.0
    assert score(make_frame({"INS_FUND_PCT": 40.0}), empty_history(), "NONE").dims["B"] == 5.0
    # BAD_DEBT_RATE > 0 floors B at 2 even with a full fund.
    res = score(
        make_frame({"INS_FUND_PCT": 100.0, "BAD_DEBT_RATE": 0.3}),
        empty_history(),
        "NONE",
    )
    assert res.dims["B"] == 2.0


def test_a_cannot_close_forces_5() -> None:
    res = score(make_frame(flags={"cannot_close": True}), empty_history(), "NONE")
    assert res.dims["A"] == 5.0


def test_r_ticket_warn_scores_1_and_critical_3() -> None:
    assert score(make_frame({"TICKET_RATE": 3.0}), empty_history(), "NONE").dims["R"] == 1.0
    assert score(make_frame({"TICKET_RATE": 8.0}), empty_history(), "NONE").dims["R"] == 3.0
    assert score(make_frame(flags={"regulatory_notice": True}), empty_history(), "NONE").dims["R"] == 5.0


def test_v_flat_signal_is_zero_and_doubling_is_5() -> None:
    hist = SignalHistory()
    hist.add(make_frame({"LIQ_RATE": 200.0}, t=-300))
    assert score(make_frame({"LIQ_RATE": 200.0}, t=0), hist, "NONE").dims["V"] == 0.0

    hist2 = SignalHistory()
    hist2.add(make_frame({"LIQ_RATE": 5.0}, t=-300))
    res = score(make_frame({"LIQ_RATE": 300.0}, t=0), hist2, "NONE")
    assert res.dims["V"] == 5.0


def test_score_formula_weights() -> None:
    # Seed history with the same hot value so velocity is flat (V = 0).
    hist = SignalHistory()
    hist.add(make_frame({"TICKET_RATE": 8.0}, t=-300))
    res = score(make_frame({"TICKET_RATE": 8.0}), hist, "NONE")
    # R = 3, everything else 0 → S = 20 × 0.15 × 3 = 9.
    assert res.score == pytest.approx(9.0)


# -- hard overrides -------------------------------------------------------------

def _history_with(code_values: dict[str, float], start_t: int, end_t: int, step: int = 2) -> SignalHistory:
    hist = SignalHistory()
    t = start_t
    while t <= end_t:
        hist.add(make_frame(code_values, t=t))
        t += step
    return hist


def test_override_wrongful_liquidation() -> None:
    frame = make_frame({"LAR": 3.2})
    hist = empty_history()
    assert score(frame, hist, "SYSTEM").overrides != []
    assert score(frame, hist, "PRICING").overrides != []
    # MARKET verdict with the same LAR is not a wrongful-liquidation override.
    assert score(frame, hist, "MARKET").overrides == []
    # Below critical LAR is not an override either.
    assert score(make_frame({"LAR": 2.5}), hist, "SYSTEM").overrides == []


def test_override_fund_and_adl() -> None:
    hist = empty_history()
    assert any("25%" in o for o in score(make_frame({"INS_FUND_PCT": 24.9}), hist, "NONE").overrides)
    assert score(make_frame({"INS_FUND_PCT": 25.0}), hist, "NONE").overrides == []
    assert any("ADL" in o for o in score(make_frame({"ADL_COUNT": 1}), hist, "NONE").overrides)


def test_override_stablecoin_held_edges() -> None:
    now = 1000
    # Full 300 s coverage → override fires.
    hist = _history_with({"STBL_PX": 0.96}, now - 400, now)
    frame = make_frame({"STBL_PX": 0.96}, t=now)
    assert any("Stablecoin" in o for o in score(frame, hist, "NONE").overrides)
    # Only 298 s of coverage (N-2 s) → no override.
    hist_short = _history_with({"STBL_PX": 0.96}, now - 298, now)
    assert not any("Stablecoin" in o for o in score(frame, hist_short, "NONE").overrides)


def test_override_cannot_close_held_edges() -> None:
    now = 2000

    def flagged(t: int) -> SignalFrame:
        return make_frame(flags={"cannot_close": True}, t=t)

    hist = SignalHistory()
    t = now - 240
    while t <= now:
        hist.add(flagged(t))
        t += 2
    frame = flagged(now)
    assert any("close" in o for o in score(frame, hist, "NONE").overrides)

    hist_short = SignalHistory()
    t = now - 178
    while t <= now:
        hist_short.add(flagged(t))
        t += 2
    assert not any("close" in o for o in score(frame, hist_short, "NONE").overrides)


def test_override_wallet_compromise_immediate() -> None:
    frame = make_frame(flags={"wallet_compromise_suspected": True})
    assert any("wallet" in o.lower() for o in score(frame, empty_history(), "NONE").overrides)


def test_severity_result_shape() -> None:
    res: SeverityResult = score(make_frame(), empty_history(), "NONE")
    assert set(res.dims) == {"F", "B", "A", "V", "R"}
