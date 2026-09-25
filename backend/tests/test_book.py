"""CrashBook tests (H1): LAR behaviour, fund monotonicity, pause queue."""

from __future__ import annotations

from incident.book import CrashBook
from incident.scenario_loader import BookSpec, ScenarioLoader, ScenarioSpec


def _scenario(px_drop: float = -0.06, lar_mult: float = 1.0, fund: float = 4_080_000.0) -> ScenarioLoader:
    spec = ScenarioSpec(
        id="T", name="t", description="t", duration_s=900, seed=42, asset="NVDA",
        book=BookSpec(insurance_fund_usd=fund),
        tracks={"PX": [[-120, 0.0], [0, px_drop], [900, px_drop]]},
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
    drops: list[tuple[int, float]] = []
    t = -120
    while t <= upto:
        px = interp_track(px_kf, t)
        lm = interp_track(lar_kf, t)
        oc = book.step(t, px, px - prev, lar_mult=lm, paused=paused)
        prev = px
        drop_now = max(0.0, -px)
        drops.append((t, drop_now))
        start = drops[0][1]
        for ht, v in drops:
            if ht <= t - 60:
                start = v
            else:
                break
        peak = max([v for ht, v in drops if t - 60 < ht <= t] + [start])
        l_obs = book.liq_rate(t)
        l_exp = book.expected_per_min(peak, start)
        from incident.book import lar_ratio

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
