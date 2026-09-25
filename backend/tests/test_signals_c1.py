"""C1 end-to-end signal tests (H1 acceptance, incl. review rows).

- Same seed -> byte-identical frames.
- Pre-roll is calm: every frame before T+0 is all-normal.
- `expected` bands from the scenario JSON pass on the no-action run.
- No-action: fund crosses 25% in T+20..28 (EMERGENCY branch).
- Reduce-only at T+18 (H3's exact control effects): fund stays > 60% and
  every frame from T+40 holds all signals below warn, which is H2's
  precondition for STABILISING -> RESOLVED by T+55.
- Every frame carries the full catalogue + PX and all flags.
- Full 3600 s replay completes in < 2 s.
"""

from __future__ import annotations

import time

from incident.catalogue import SIGNALS, status_of
from incident.clock import TICK_S
from incident.contracts import Effect, SignalFrame
from incident.scenario_loader import ScenarioLoader
from incident.signals import FLAG_CODES, SignalGenerator

CODES = {s.code for s in SIGNALS} | {"PX"}

# H3 reduce_only control, verbatim (backend/incident/content/controls.py):
# sim.new_exposure steers the book price path; the LIQ_RATE mult trims the
# displayed cascade (fewer new positions opening).
REDUCE_ONLY = [
    (Effect(signal="sim.new_exposure", op="set", value=0.0, ramp_s=60), 1080),
    (Effect(signal="LIQ_RATE", op="mult", value=0.6, ramp_s=120), 1080),
]


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


def test_preroll_is_calm():
    """Review row 1: T-2:00..T+0 is NORMAL — no liquidation, no bad debt."""
    frames = _replay(upto=0)
    for t, f in frames.items():
        if t >= 0:
            continue
        assert f.values["LIQ_RATE"] == 0.0, t
        assert f.values["BAD_DEBT_RATE"] == 0.0, t
        assert f.values["NEG_BAL_ACCTS"] == 0.0, t
        assert f.values["INS_FUND_PCT"] == 100.0, t
        assert f.values["PX_CHG_5M"] == 0.0, t
        for code, v in f.values.items():
            if code == "PX":
                continue
            assert status_of(code, v) == "normal", (t, code, v)


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
    # Crash starts at T+0 (flat pre-roll before it); liquidations ramp.
    assert frames[0].values["LIQ_RATE"] < 100
    assert frames[120].values["LIQ_RATE"] >= 50
    assert frames[240].values["LIQ_RATE"] >= 100
    # T+6: tickets ~4x baseline (I1).
    assert 3.0 <= frames[360].values["TICKET_RATE"] <= 5.0
    # T+14: critical rate, fund still intact (waterfall comes later).
    assert 250 <= frames[840].values["LIQ_RATE"] <= 550
    assert frames[840].values["INS_FUND_PCT"] >= 95
    # LAR stays market-explained through the crash.
    for t in (120, 360, 840, 1080, 1440):
        if frames[t].values["LIQ_RATE"] >= 10.0:
            assert 0.7 <= frames[t].values["LAR"] <= 1.5, (t, frames[t].values["LAR"])


def test_c1_has_no_short_liquidations():
    """The LAR denominator models long crossings only; C1 must not break
    that assumption (no rallies above start)."""
    gen = SignalGenerator(ScenarioLoader.from_id("C1"))
    t = -120
    while t <= 3360:
        gen.step(t)
        t += TICK_S
    assert gen.book.n_short_liq == 0, gen.book.n_short_liq


def test_no_action_crosses_25pct_between_T20_T28():
    """Review row 2: no-action EMERGENCY branch via the fund override."""
    frames = _replay()
    crossing = next(t for t in sorted(frames) if frames[t].values["INS_FUND_PCT"] < 25)
    assert 1200 <= crossing <= 1680, crossing


def test_reduce_only_at_T18_contains_cascade():
    """Review row 3: fund survives and signals clear for a T+55 resolve."""
    frames = _replay(effects=REDUCE_ONLY)
    funds = [f.values["INS_FUND_PCT"] for f in frames.values()]
    assert min(funds) > 60, min(funds)
    assert frames[2700].values["LIQ_RATE"] < 50
    # H2 resolve precondition: every signal below warn, sustained. The state
    # machine needs 15 min of it plus IC confirmation, so it must hold from
    # T+40 at the latest for a resolve by T+55.
    for t, f in frames.items():
        if t < 2400:
            continue
        for code, v in f.values.items():
            if code == "PX":
                continue
            st = status_of(code, v)
            assert st not in ("warn", "critical"), (t, code, v, st)


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
