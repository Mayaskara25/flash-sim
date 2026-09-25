"""CrashBook tests (H1): LAR behaviour, fund monotonicity, pause queue."""

from __future__ import annotations

from incident.book import CrashBook, lar_ratio
from incident.scenario_loader import BookSpec, ScenarioLoader, ScenarioSpec


def _scenario(px_drop: float = -0.06, lar_mult: float = 1.0, fund: float = 135_000.0, capacity: float | None = None) -> ScenarioLoader:
    # slippage is a depth-based execution-gap factor now (book.py:
    # `slip = slippage * |cumulative drawdown|`), not a tick-delta
    # multiplier; 0.3 is a representative C1-scale value.
    spec = ScenarioSpec(
        id="T", name="t", description="t", duration_s=900, seed=42, asset="NVDA",
        book=BookSpec(insurance_fund_usd=fund, slippage=0.3, liq_capacity_per_min=capacity),
        tracks={"PX": [[-120, 0.0], [0, 0.0], [240, px_drop], [900, px_drop]]},
        faults={"LAR_MULT": [[-120, lar_mult]]},
    )
    return ScenarioLoader(spec)


def _run(scenario: ScenarioLoader, upto: int = 300, paused: bool = False):
    from incident.scenario_loader import interp_track

    book = CrashBook(scenario)
    px_kf = scenario.spec.tracks["PX"]
    lar_kf = scenario.spec.faults["LAR_MULT"]
    prev = interp_track(px_kf, -120)
    lars, funds, rates = [], [], []
    t = -120
    while t <= upto:
        px = interp_track(px_kf, t)
        lm = interp_track(lar_kf, t)
        book.step(t, px, px - prev, lar_mult=lm, paused=paused)
        prev = px
        l_obs = book.liq_rate(t)
        l_exp = book.expected_liq_rate(t)
        lar = lar_ratio(l_obs, l_exp)
        lars.append(lar)
        funds.append(book.fund_pct)
        rates.append(l_obs)
        t += 2
    return book, lars, funds, rates


def test_lar_near_one_on_pure_market_move():
    _, lars, _, rates = _run(_scenario(px_drop=-0.06), upto=300)
    crash_lars = [(i * 2 - 120, l) for i, (l, r) in enumerate(zip(lars, rates)) if r >= 1.0]
    assert crash_lars, "expected measurable liquidations in a -6% crash"
    # Full 60 s windows exist from T-60; there the book-vs-table comparison
    # is exact up to grid interpolation and must sit in 0.7-1.5.
    steady = [l for t, l in crash_lars if t >= -60]
    assert steady, "expected measurable liquidations with full windows"
    assert min(steady) >= 0.7, steady
    assert max(steady) <= 1.5, steady
    # During warmup (partially filled rolling windows + sparse book tail)
    # LAR may wobble but must stay below the warn threshold (2.0), so H2
    # never tags a system fault on replay-start noise.
    assert max(l for _, l in crash_lars) < 2.0, crash_lars


def test_lar_high_with_engine_bug_multiplier():
    _, lars, _, rates = _run(_scenario(px_drop=-0.02, lar_mult=3.5), upto=300)
    hot = [l for l, r in zip(lars, rates) if r >= 1.0]
    assert hot, "expected measurable liquidations for the LAR>3 check"
    assert max(hot) > 3.0, hot


def test_fund_decreases_monotonically_without_topup():
    _, _, funds, _ = _run(_scenario(px_drop=-0.10), upto=600)
    for a, b in zip(funds, funds[1:]):
        assert b <= a + 1e-9


def test_pause_queues_and_flushes():
    scenario = _scenario(px_drop=-0.10)
    book = CrashBook(scenario)
    from incident.scenario_loader import interp_track

    px_kf = scenario.spec.tracks["PX"]
    prev = interp_track(px_kf, -120)
    t = -120
    peak_queued = 0
    while t <= 120:
        px = interp_track(px_kf, t)
        oc = book.step(t, px, px - prev, paused=True)
        assert oc.n_new_scaled == 0.0
        peak_queued = max(peak_queued, oc.queued)
        prev = px
        t += 2
    assert peak_queued > 0, "pause must queue crossings during a crash"
    flushed = 0
    while t <= 400 and book.queue:
        px = interp_track(px_kf, t)
        oc = book.step(t, px, px - prev, paused=False)
        flushed += oc.n_new_raw
        prev = px
        t += 2
    assert flushed > 0, "unpause must flush the backlog"


def test_capacity_is_bounded_without_banking_idle_credit():
    scenario = _scenario(px_drop=-0.10, capacity=120)
    book = CrashBook(scenario)
    from incident.scenario_loader import interp_track

    track = scenario.spec.tracks["PX"]
    previous = interp_track(track, -120)
    outcomes = []
    rates = []
    for t in range(-120, 301, 2):
        px = interp_track(track, t)
        outcomes.append(book.step(t, px, px - previous))
        rates.append(book.liq_rate(t))
        previous = px
    assert max(item.n_new_raw for item in outcomes) <= 4  # 120/min × 2 s
    assert max(rates) <= 120
    assert any(item.queued > 0 for item in outcomes)
    assert book.expected_liq_rate(300) == book.liq_rate(300)
