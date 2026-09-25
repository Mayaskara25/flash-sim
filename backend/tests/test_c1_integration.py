"""C1 integration test (Part C, H1+H2 end-to-end).

Replays real C1 frames from `SignalGenerator` through `SignalHistory` ->
`classify` -> `score` -> `StateMachine.step`, auto-confirming any IC-pending
step-down/resolve once per sim-minute (matching the cadence of an IC who
glances at the console roughly once a minute, not every 2 s tick). Adapted
from the scratch script used while verifying the H1/H2 handoffs end-to-end.

This is the only place that exercises H1's signal generator and H2's rules
engine together; H1 and H2 each test their own layer against hand-built or
scripted frames in isolation.
"""

from __future__ import annotations

from incident.clock import TICK_S
from incident.content.controls import CONTROLS
from incident.contracts import Effect
from incident.rules.classifier import classify
from incident.rules.history import SignalHistory
from incident.rules.severity import score
from incident.rules.state_machine import StateMachine
from incident.scenario_loader import ScenarioLoader
from incident.signals import SignalGenerator

BAD_VERDICTS = {"SYSTEM", "PRICING", "COLLATERAL"}


def _run(
    effects: list[Effect] | None = None,
    approve_at: int | None = None,
    upto: int = 3600,
) -> dict[int, dict]:
    """Replay C1 through the full H1 -> H2 pipeline.

    Returns ``{t: {"state", "verdict", "overrides", "score", "fund"}}``.
    """
    gen = SignalGenerator(ScenarioLoader.from_id("C1"))
    sm = StateMachine()
    hist = SignalHistory()
    eff: list[tuple[Effect, int]] = []
    out: dict[int, dict] = {}
    t = -120
    while t <= upto:
        if effects and approve_at is not None and t == approve_at:
            eff = [(e, approve_at) for e in effects]
        frame = gen.step(t, eff)
        hist.add(frame)
        c = classify(frame, hist)
        s = score(frame, hist, c.verdict)
        state, _ = sm.step(t, s, frame)
        if sm.pending is not None and t % 60 == 0:
            sm.confirm("IC", t)
            state = sm.state
        out[t] = {
            "state": state,
            "verdict": c.verdict,
            "overrides": s.overrides,
            "score": s.score,
            "fund": frame.values["INS_FUND_PCT"],
            "liq": frame.values["LIQ_RATE"],
        }
        t += TICK_S
    return out


def test_preroll_never_above_watch():
    """Pre-roll (T-2:00..T+0) never exceeds WATCH."""
    recs = _run(upto=0)
    for t, r in recs.items():
        if t >= 0:
            continue
        assert r["state"] in ("NORMAL", "WATCH"), (t, r["state"])


def test_warning_by_T3_critical_by_T15():
    recs = _run(upto=900)
    assert any(r["state"] == "WARNING" for t, r in recs.items() if 0 <= t <= 180), (
        "expected WARNING by T+3"
    )
    assert any(
        r["state"] in ("CRITICAL", "EMERGENCY") for t, r in recs.items() if 0 <= t <= 900
    ), "expected CRITICAL by T+15"
    for minute in range(1, 12):
        row = recs[minute * 60]
        assert row["state"] == "WARNING", (minute, row)
        assert 100 <= row["liq"] <= 290, (minute, row)
        assert row["score"] < 50, (minute, row)
    first_critical = min(t for t, row in recs.items() if row["state"] == "CRITICAL")
    assert 660 < first_critical <= 900, first_critical


def test_classifier_never_system_pricing_collateral():
    recs = _run(upto=3600)
    for t, r in recs.items():
        assert r["verdict"] not in BAD_VERDICTS, (t, r["verdict"])


def test_no_action_emergency_T20_T28_with_fund_override():
    recs = _run(upto=1680)
    window = {t: r for t, r in recs.items() if 1200 <= t <= 1680}
    assert any(r["state"] == "EMERGENCY" for r in window.values()), (
        "expected EMERGENCY between T+20 and T+28"
    )
    assert any(
        r["state"] == "EMERGENCY"
        and any("Insurance fund below 25%" in o for o in r["overrides"])
        for r in window.values()
    ), "expected the fund override active while EMERGENCY in T+20..T+28"


def test_reduce_only_at_T18_never_emergency_resolves_by_T58():
    reduce_only = CONTROLS["reduce_only"].effects
    recs = _run(effects=reduce_only, approve_at=1080, upto=3600)
    assert all(r["state"] != "EMERGENCY" for r in recs.values()), (
        "reduce-only run must never reach EMERGENCY"
    )
    resolved_at = [t for t, r in recs.items() if r["state"] == "RESOLVED"]
    assert resolved_at, "reduce-only run never reached RESOLVED"
    assert min(resolved_at) <= 3480, min(resolved_at)  # T+58:00
