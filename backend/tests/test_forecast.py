"""Forecast lead time, paired what-ifs, determinism and runtime."""

from time import perf_counter

from incident.forecast import compute
from incident.session import IncidentSession


def at(session, wall, minute):
    wall[0] = minute * 60 / 8
    return session.to_dto()


def test_c1_early_warning_and_control_directions():
    wall = [0.]
    session = IncidentSession(lambda: wall[0])
    session.start("C1", 8)
    dto = at(session, wall, 14)
    assert dto.forecast.label == "Simulated projection — not a market forecast"
    assert dto.forecast.n_paths == 200
    assert dto.forecast.eta_sev1_min.prob_within_15 > .5
    controls = {a.control_id: a.what_if for a in dto.actions if a.what_if}
    assert controls["reduce_only"].p_sev1_15_before - controls["reduce_only"].p_sev1_15_after >= .25
    assert controls["ins_fund_topup"].fund_p50_15_after > controls["ins_fund_topup"].fund_p50_15_before
    assert 0 <= dto.forecast.cascade_model_p <= 1
    assert all(abs(sum(point.p.values()) - 1) < 1e-9 for point in dto.forecast.sev_probs)


def test_after_reduce_only_risk_stays_low():
    wall = [0.]
    session = IncidentSession(lambda: wall[0])
    session.start("C1", 8)
    at(session, wall, 14 + 40 / 60)
    session.decide("M2.2", "approve", "IC", "Reduce exposure")
    for minute in (20, 25, 30):
        dto = at(session, wall, minute)
        assert dto.forecast.eta_sev1_min.prob_within_15 < .3


def test_same_tick_is_deterministic_and_under_budget():
    wall = [0.]
    session = IncidentSession(lambda: wall[0])
    session.start("C1", 8)
    at(session, wall, 14)
    started = perf_counter()
    first, whatifs = compute(session)
    elapsed_ms = (perf_counter() - started) * 1000
    second, repeated = compute(session)
    assert first == second and whatifs == repeated
    assert elapsed_ms < 150
