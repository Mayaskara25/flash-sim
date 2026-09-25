"""State machine: targets, hysteresis, pending confirmations (H2, SPEC §9.3)."""

from __future__ import annotations

import pytest

from incident.catalogue import SIGNALS
from incident.contracts import SignalFrame
from incident.rules.classifier import classify
from incident.rules.history import SignalHistory
from incident.rules.severity import score
from incident.rules.state_machine import StateMachine, sev_of_state

ALL_FLAGS = (
    "cannot_close",
    "wallet_compromise_suspected",
    "regulatory_notice",
    "partner_notice",
    "media_attention",
    "stablecoin_frozen_address",
)


def make_frame(values: dict[str, float] | None = None, t: int = 0) -> SignalFrame:
    base = {s.code: float(s.baseline) for s in SIGNALS}
    base.update(values or {})
    return SignalFrame(
        t=t, values=base, flags={code: False for code in ALL_FLAGS}, meta={}
    )


def step_at(sm: StateMachine, hist: SignalHistory, t: int, values: dict[str, float]):
    frame = make_frame(values, t=t)
    hist.add(frame)
    res = classify(frame, hist)
    sev = score(frame, hist, res.verdict)
    return sm.step(t, sev, frame)


def test_upward_moves_are_immediate() -> None:
    sm, hist = StateMachine(), SignalHistory()
    state, events = step_at(sm, hist, 0, {"LIQ_RATE": 120.0})  # warn
    assert state == "WARNING"
    assert len(events) == 1
    state, events = step_at(sm, hist, 2, {"LIQ_RATE": 400.0})  # critical
    assert state == "CRITICAL"


def test_sev_mapping() -> None:
    assert sev_of_state("EMERGENCY") == 1
    assert sev_of_state("CRITICAL") == 2
    assert sev_of_state("WARNING") == 3
    assert sev_of_state("NORMAL") == 4
    assert sev_of_state("WATCH") == 4
    assert sev_of_state("RESOLVED") == 4
    assert sev_of_state("STABILISING", prior_sev=1) == 1
    assert sev_of_state("STABILISING", prior_sev=2) == 2


def test_override_forces_emergency() -> None:
    sm, hist = StateMachine(), SignalHistory()
    state, _ = step_at(sm, hist, 0, {"INS_FUND_PCT": 22.0})
    assert state == "EMERGENCY"


def test_down_from_critical_needs_5min_and_ic() -> None:
    sm, hist = StateMachine(), SignalHistory()
    step_at(sm, hist, 0, {"LIQ_RATE": 400.0})
    assert sm.state == "CRITICAL"
    # 4 min below band: still CRITICAL, no pending yet.
    t = 2
    while t <= 240:
        step_at(sm, hist, t, {})
        t += 2
    assert sm.state == "CRITICAL"
    assert sm.pending is None
    # Past 5 min below band: pending stepdown proposed, still CRITICAL.
    while t <= 320:
        step_at(sm, hist, t, {})
        t += 2
    assert sm.state == "CRITICAL"
    assert sm.pending is not None
    assert sm.pending.kind == "stepdown"
    assert sm.pending.to_state == "STABILISING"
    # Non-IC confirmation is rejected.
    with pytest.raises(ValueError):
        sm.confirm("TL", t)
    assert sm.state == "CRITICAL"
    sm.confirm("IC", t)
    assert sm.state == "STABILISING"


def test_warning_steps_down_automatically_after_5min() -> None:
    sm, hist = StateMachine(), SignalHistory()
    step_at(sm, hist, 0, {"LIQ_RATE": 120.0})
    assert sm.state == "WARNING"
    t = 2
    while t <= 400:
        state, _ = step_at(sm, hist, t, {})
        t += 2
    assert state in ("WATCH", "NORMAL")


def test_oscillation_gives_at_most_one_downward_move_in_10min() -> None:
    sm, hist = StateMachine(), SignalHistory()
    step_at(sm, hist, 0, {"LIQ_RATE": 400.0})
    assert sm.state == "CRITICAL"
    downs = 0
    prev = sm.state
    rank = {"NORMAL": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3, "EMERGENCY": 4,
            "STABILISING": 5, "RESOLVED": 6}
    t = 2
    while t <= 600:  # 10 min, 60 s period around the 300/min line
        phase = (t // 30) % 2
        step_at(sm, hist, t, {"LIQ_RATE": 350.0 if phase == 0 else 250.0})
        if rank[sm.state] < rank[prev]:
            downs += 1
        prev = sm.state
        t += 2
    assert downs <= 1


def test_stabilising_recritical_on_critical_recross() -> None:
    sm, hist = StateMachine(), SignalHistory()
    step_at(sm, hist, 0, {"LIQ_RATE": 400.0})
    t = 2
    while t <= 400:
        step_at(sm, hist, t, {})
        t += 2
    sm.confirm("IC", t)
    assert sm.state == "STABILISING"
    state, _ = step_at(sm, hist, t + 2, {"LIQ_RATE": 500.0})
    assert state == "CRITICAL"


def test_stabilising_resolves_after_15min_below_warn_plus_ic() -> None:
    sm, hist = StateMachine(), SignalHistory()
    step_at(sm, hist, 0, {"LIQ_RATE": 400.0})
    t = 2
    while t <= 400:
        step_at(sm, hist, t, {})
        t += 2
    sm.confirm("IC", t)
    assert sm.state == "STABILISING"
    assert sm.pending is None
    while t <= 400 + 950:
        step_at(sm, hist, t, {})
        t += 2
    assert sm.pending is not None
    assert sm.pending.kind == "resolve"
    sm.confirm("IC", t)
    assert sm.state == "RESOLVED"


def test_manual_raise_only_goes_up() -> None:
    sm = StateMachine(since_t=0)
    sm.state = "WARNING"
    assert sm.manual_raise(2, t=10)  # SEV-2 → CRITICAL
    assert sm.state == "CRITICAL"
    assert sm.manual_raise(3, t=12) == []  # SEV-3 would lower: refused
    assert sm.state == "CRITICAL"


def test_c1_replay_warning_near_t0_critical_near_t14() -> None:
    """Hand-built C1 spine (SPEC §12.2): WARNING ~T+0, CRITICAL ~T+14."""
    sm, hist = StateMachine(), SignalHistory()
    states: dict[int, str] = {}
    c1 = [
        (-120, {"PX_CHG_5M": 0.0, "LIQ_RATE": 5.0, "INS_FUND_PCT": 100.0, "TICKET_RATE": 1.0}),
        (0, {"PX_CHG_5M": -6.0, "LIQ_RATE": 120.0, "LAR": 1.1, "TICKET_RATE": 1.4}),
        (360, {"PX_CHG_5M": -7.0, "LIQ_RATE": 200.0, "LAR": 1.1, "TICKET_RATE": 4.1,
               "SENTIMENT": -0.3, "INS_FUND_PCT": 80.0}),
        (840, {"PX_CHG_5M": -9.8, "LIQ_RATE": 410.0, "LAR": 1.1, "INS_FUND_PCT": 40.0,
               "BAD_DEBT_RATE": 0.4, "TICKET_RATE": 4.3, "SENTIMENT": -0.38}),
    ]
    for t, values in c1:
        state, _ = step_at(sm, hist, t, values)
        states[t] = state
    assert states[0] == "WARNING"
    assert states[840] == "CRITICAL"
