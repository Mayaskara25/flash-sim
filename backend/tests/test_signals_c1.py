"""C1 end-to-end signal tests (H1 acceptance, incl. review rows).

- Same seed -> byte-identical frames.
- Pre-roll (T-2:00..T+0): every signal stays at watch or below (PX starts
  falling at ~T-0:30 per SCHEMA.md, so LIQ_RATE is not exactly zero right
  at T+0, but nothing reaches warn).
- `expected` bands from the scenario JSON pass on the no-action run.
- No-action: fund crosses 25% between T+20 and T+26 (EMERGENCY branch via
  the fund override); LAR stays market-explained (0.7-1.5) throughout;
  BAD_DEBT_RATE turns on gradually from ~T+3, not as a one-tick cliff.
- Reduce-only at T+18 (H3's exact control effects): fund never drops below
  25% (comfortably above, ~34% floor) and LIQ_RATE < 50/min by T+45.
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
    """Review row 1: T-2:00..T+0 never exceeds WATCH (rules stay NORMAL/WATCH).

    PX is flat through T-0:30 (SCHEMA.md), so everything is strictly zero
    and every status is "normal" up to there. From T-0:30 to T+0 the crash
    has begun (by design, target #1: "PX flat until ~T-0:30, then falls"),
    so a few liquidations trickle in, but every signal must stay at watch
    or below the whole way to T+0 -- never warn/critical.
    """
    frames = _replay(upto=0)
    for t, f in frames.items():
        if t <= -30:
            assert f.values["LIQ_RATE"] == 0.0, t
            assert f.values["BAD_DEBT_RATE"] == 0.0, t
            assert f.values["NEG_BAL_ACCTS"] == 0.0, t
            assert f.values["INS_FUND_PCT"] == 100.0, t
            assert f.values["PX_CHG_5M"] == 0.0, t
            for code, v in f.values.items():
                if code == "PX":
                    continue
                assert status_of(code, v) == "normal", (t, code, v)
        else:
            for code, v in f.values.items():
                if code == "PX":
                    continue
                assert status_of(code, v) in ("normal", "watch"), (t, code, v)


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
    """Part A targets 2-4: crash speed, ticket surge, LAR."""
    frames = _replay()
    # PX flat until ~T-0:30, then falls: PX_CHG_5M <= -5 (warn) within
    # T+0..T+3, LIQ_RATE >= 100/min by T+2.
    assert frames[0].values["PX_CHG_5M"] > -5.0
    assert frames[180].values["PX_CHG_5M"] <= -5.0
    assert frames[120].values["LIQ_RATE"] >= 100
    # T+6: tickets ~4x baseline (I1).
    assert 3.0 <= frames[360].values["TICKET_RATE"] <= 5.0
    # T+14: LIQ_RATE 350-500/min, fund drained to 35-45% (gradual waterfall,
    # not the 90-100% "fund still intact" of the pre-recalibration track).
    assert 350 <= frames[840].values["LIQ_RATE"] <= 500
    assert 35 <= frames[840].values["INS_FUND_PCT"] <= 45
    # LAR stays market-explained (0.7-1.5) throughout, never SYSTEM/PRICING.
    for t in sorted(frames):
        if t < 0:
            continue
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


def test_no_action_crosses_25pct_between_T20_T26():
    """Part A target 5 / review row 2: no-action EMERGENCY branch via the
    fund override, and BAD_DEBT_RATE turns on gradually from ~T+3 (not a
    cliff): no single tick should account for a huge jump once the crash
    is under way."""
    frames = _replay()
    crossing = next(t for t in sorted(frames) if frames[t].values["INS_FUND_PCT"] < 25)
    assert 1200 <= crossing <= 1560, crossing
    # Gradual: BAD_DEBT_RATE > 0 from around T+3 onward (not first appearing
    # right at the crossing, i.e. not a single-tick cliff from 100% to <25%).
    first_bad_debt = next(t for t in sorted(frames) if frames[t].values["BAD_DEBT_RATE"] > 0)
    assert 120 <= first_bad_debt <= 300, first_bad_debt


def test_reduce_only_at_T18_contains_cascade():
    """Part A target 7 / review row 3: fund never drops below 25% (stays
    comfortably above it) and LIQ_RATE < 50/min by T+45."""
    frames = _replay(effects=REDUCE_ONLY)
    funds = [f.values["INS_FUND_PCT"] for f in frames.values()]
    assert min(funds) >= 25, min(funds)
    assert frames[2700].values["LIQ_RATE"] < 50
    # H2 resolve precondition: every signal below warn *except*
    # INS_FUND_PCT, sustained. The fund settles around 34%, which is
    # below the 60% warn line without a top-up -- exactly the case H2's
    # resolve rule (PLAN §3 decision #13) special-cases: INS_FUND_PCT
    # counts as "settled" when it is above critical (25) and flat, not
    # strictly below warn. It must never reach critical here though.
    for t, f in frames.items():
        if t < 2400:
            continue
        for code, v in f.values.items():
            if code in ("PX", "INS_FUND_PCT"):
                continue
            st = status_of(code, v)
            assert st not in ("warn", "critical"), (t, code, v, st)
        assert status_of("INS_FUND_PCT", f.values["INS_FUND_PCT"]) != "critical", (
            t, f.values["INS_FUND_PCT"],
        )


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
