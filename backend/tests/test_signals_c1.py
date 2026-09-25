"""C1 end-to-end signal tests (H1 acceptance).

- Same seed -> byte-identical frames.
- `expected` bands from the scenario JSON pass on the no-action run.
- No-action: fund crosses 25% in T+22..26 (T+1320..1560).
- Reduce-only at T+18: fund stays > 30%, LIQ_RATE < 50/min by T+45.
- Every frame carries the full catalogue + PX and all flags.
- Full 3600 s replay completes in < 2 s.
"""

from __future__ import annotations

import time

import pytest

from incident.catalogue import SIGNALS
from incident.clock import TICK_S
from incident.contracts import Effect, SignalFrame
from incident.scenario_loader import ScenarioLoader
from incident.signals import FLAG_CODES, SignalGenerator

CODES = {s.code for s in SIGNALS} | {"PX"}

REDUCE_ONLY = [(Effect(signal="sim.new_exposure", op="set", value=0.0, ramp_s=60), 1080)]


def _replay(seed: int = 42, effects=None, upto: int = 3360) -> dict[int, SignalFrame]:
    gen = SignalGenerator(ScenarioLoader.from_id("C1"), seed=seed)
    out: dict[int, SignalFrame] = {}
    t = -120
    while t <= upto:
        out[t] = gen.step(t, effects)
        t += TICK_S
    return out


def test_same_seed_byte_identical_frames():
    a = _replay(upto=900)
    b = _replay(upto=900)
    assert a.keys() == b.keys()
    for t in a:
        assert a[t].values == b[t].values, t
        assert a[t].flags == b[t].flags, t
        assert a[t].meta == b[t].meta, t


def test_frames_carry_full_catalogue_and_flags():
    frames = _replay(upto=100)
    for t, f in frames.items():
        assert set(f.values) == CODES, t
        assert set(f.flags) == set(FLAG_CODES), t
        assert f.t == t


def test_expected_bands_no_action():
    loader = ScenarioLoader.from_id("C1")
    frames = _replay()
    for point in loader.spec.expected:
        t = point["t"]
        f = frames[t]
        for code, band in point.items():
            if code == "t":
                continue
            lo, hi = band
            v = f.values[code]
            assert lo <= v <= hi, f"T+{t} {code}={v} not in [{lo}, {hi}]"


def test_c1_markers():
    frames = _replay()
    # T+0: -6% in 5 min -> warn; liquidation warning level.
    assert frames[0].values["PX_CHG_5M"] == pytest.approx(-6.0, abs=0.05)
    assert frames[0].values["LIQ_RATE"] >= 100
    # T+6: tickets ~4x baseline (I1).
    assert 3.0 <= frames[360].values["TICKET_RATE"] <= 5.0
    # T+14: critical rate, fund in the 30-50 band.
    assert 300 <= frames[840].values["LIQ_RATE"] <= 550
    assert 30 <= frames[840].values["INS_FUND_PCT"] <= 50
    # LAR stays market-explained through the crash.
    for t in (0, 360, 840, 1080):
        if frames[t].values["LIQ_RATE"] >= 1.0:
            assert 0.7 <= frames[t].values["LAR"] <= 1.5, (t, frames[t].values["LAR"])


def test_no_action_crosses_25pct_between_T22_T26():
    frames = _replay()
    crossing = next(t for t in sorted(frames) if frames[t].values["INS_FUND_PCT"] < 25)
    assert 1320 <= crossing <= 1560, crossing


def test_reduce_only_at_T18_contains_cascade():
    frames = _replay(effects=REDUCE_ONLY)
    funds = [f.values["INS_FUND_PCT"] for f in frames.values()]
    assert min(funds) > 30, min(funds)
    assert frames[2700].values["LIQ_RATE"] < 50
    # Recovery still completes.
    assert frames[3300].values["LIQ_RATE"] < 50
    assert frames[3300].values["INS_FUND_PCT"] > 30


def test_full_replay_under_two_seconds():
    gen = SignalGenerator(ScenarioLoader.from_id("C1"))
    start = time.perf_counter()
    t = -120
    n = 0
    while t <= 3600:
        gen.step(t)
        t += TICK_S
        n += 1
    dt = time.perf_counter() - start
    assert n == 1861, n
    assert dt < 2.0, f"{dt:.2f}s for {n} ticks"
