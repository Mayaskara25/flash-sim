"""Seeded, simulation-only incident projections with common-random-number what-ifs.

The live book supplies open-position thresholds and observed loss/throughput.
Paths run at ten simulated seconds, using declining price momentum and a
decaying liquidation backlog. This is a conditional incident projection, not
an estimate of real market returns.
"""

from __future__ import annotations

import numpy as np

from cascade_model.model import evaluate

from .contracts import Driver, EtaEstimate, Forecast, InsFundPoint, SevProbPoint, WhatIf

N_PATHS = 200
STEP_S = 10
STEPS = 90
HORIZONS = (5, 10, 15)


def _cascade_probability(session) -> float:
    book = session.generator.book
    values = session.frame.values
    drop = abs(float(values.get("PX", 0)))
    liq = float(values.get("LIQ_RATE", 0))
    cap = book.capacity_per_min or max(liq, 1)
    outstanding = np.count_nonzero(~book.liquidated)
    near = np.count_nonzero((book._long_d > drop) & (book._long_d < drop + .02))
    features = {
        "price_drop": min(drop, .25),
        "volatility": max(.5, min(2.2, abs(values.get("PX_CHG_5M", 0)) / 5 + .5)),
        "volume_change": min(8., liq / 100),
        "average_leverage": float(np.mean(book.lev)),
        "near_liquidation_ratio": min(.45, near / max(outstanding, 1)),
        "liquidation_ratio": min(.35, float(np.mean(book.liquidated))),
        "liquidation_concentration": .4,
        "long_short_imbalance": abs(2 * float(np.mean(book.is_long)) - 1),
        "liquidity_score": max(.3, 1 - .7 * liq / max(cap, 1)),
        "recent_liquidation_rate": min(.4, liq / max(book.n_total, 1)),
    }
    return float(evaluate(features)["sklearn_probability"])


def _paths(session, shocks: np.ndarray, cascade_p: float, control_id: str | None):
    frame = session.frame
    current_fund = float(frame.values["INS_FUND_PCT"])
    book = session.generator.book
    recent_fund = session.history.value_at("INS_FUND_PCT", frame.t - 60)
    fund_trend = max(0., (recent_fund - current_fund) if recent_fund is not None else 0.)
    bad_debt = max(0., float(frame.values["BAD_DEBT_RATE"]))
    rate = max(fund_trend, bad_debt)
    # A queue of crossed positions still has loss potential even on a bounce.
    queued = len(book.queue) / max(book.capacity_per_min or 360, 1)
    rate += min(1.2, queued) * max(0., bad_debt) * .1
    # The one-minute observed rate can spike as a throughput queue drains;
    # projecting that peak unchanged for 15 minutes would imply more debt
    # than the remaining book can create. Limit the initial rate, then decay.
    rate = min(rate, 7.0)
    price_now = float(frame.values.get("PX", 0.))
    px_ago = session.history.value_at("PX_CHG_5M", frame.t - 180)
    current_px5 = float(frame.values.get("PX_CHG_5M", 0.))
    momentum = np.clip((current_px5 - (px_ago if px_ago is not None else current_px5)) / 180, -.00015, .00015)
    recent = session.history.frames_in(frame.t - 300, frame.t)
    increments = np.diff([f.values.get("PX", price_now) for f in recent])
    sigma = max(.00018, float(np.std(increments)) * np.sqrt(5)) if len(increments) else .00018
    sigma = min(sigma, .002)
    # The existing cascade model increases the left-tail drift, as specified
    # in H7; the same shocks are reused for every control counterfactual.
    tail = (np.arange(N_PATHS) < N_PATHS // 10)[:, None]
    decay = np.exp(-np.arange(STEPS) * STEP_S * np.log(2) / 600)
    drift = momentum * STEP_S * decay
    drift = np.where(tail & (drift < 0), drift * (1 + cascade_p), drift)
    path_price = price_now + np.cumsum(drift + sigma * shocks, axis=1)
    # New threshold crossings are estimated from the same sorted live-book
    # long-position thresholds used by H1's expected-liquidation calculation.
    drawdown = np.maximum.accumulate(np.maximum(-path_price, 0), axis=1)
    crossed = np.searchsorted(book._long_d, drawdown.ravel(), side="right").reshape(N_PATHS, STEPS)
    initial_crossed = int(np.searchsorted(book._long_d, max(-price_now, 0), side="right"))
    crossing_rate = np.maximum(crossed - initial_crossed, 0) / max(book.n_total, 1)
    crossing_rate = np.clip(crossing_rate * 12, 0, 2)
    multiplier = np.exp(np.clip(shocks, -2, 2) * .12)
    base_drain = rate / 6 * np.exp(-np.arange(STEPS) * STEP_S * np.log(2) / 120)
    drain = base_drain[None, :] * multiplier * (1 + crossing_rate * .2)
    if control_id == "reduce_only":
        drain *= .12
    elif control_id == "raise_mm":
        drain *= .75
    elif control_id == "pause_liqs":
        drain[:, :60] = 0
    elif control_id == "collateral_haircut":
        drain *= .7
    elif control_id == "leverage_cap":
        # Only new positions are capped; existing liquidation risk remains.
        drain *= .95
    topup = 20. if control_id == "ins_fund_topup" else 0.
    fund = np.clip(current_fund + topup - np.cumsum(drain, axis=1), 0, 120)
    return path_price, fund


def _estimate_eta(hit: np.ndarray) -> EtaEstimate:
    first = np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, 0)
    reached = first[first > 0] * STEP_S / 60
    return EtaEstimate(p50=float(np.median(reached)) if len(reached) else None,
                       p90=float(np.quantile(reached, .9)) if len(reached) else None,
                       prob_within_15=float(len(reached) / len(first)))


def _project(session, shocks: np.ndarray, cascade_p: float, control_id: str | None = None):
    prices, fund = _paths(session, shocks, cascade_p, control_id)
    # The hard insurance override dominates C1. The score branch uses the
    # current H2 score and projected price stress to retain non-fund hazards.
    baseline = session.severity.score
    price_stress = np.maximum(0, (-prices - max(0, -float(session.frame.values.get("PX", 0)))) * 150)
    score = baseline + price_stress + np.maximum(0, 40 - fund) * .2
    sev1 = (fund < 25) | (score >= 70)
    sev2 = (score >= 50) | (fund < 60)
    sev3 = score >= 30
    levels = np.where(sev1, 1, np.where(sev2, 2, np.where(sev3, 3, 4)))
    probs = []
    for horizon in HORIZONS:
        index = horizon * 60 // STEP_S - 1
        probs.append(SevProbPoint(h=horizon,
            p={str(level): float(np.mean(levels[:, index] == level)) for level in (1, 2, 3, 4)}))
    fund_points = [InsFundPoint(h=h, p10=float(np.quantile(fund[:, h * 6 - 1], .1)),
                                p50=float(np.median(fund[:, h * 6 - 1])),
                                p90=float(np.quantile(fund[:, h * 6 - 1], .9))) for h in HORIZONS]
    return probs, fund_points, _estimate_eta(sev1), _estimate_eta(fund < 25)


def compute(session) -> tuple[Forecast, dict[str, WhatIf]]:
    tick = session.frame.t // STEP_S
    rng = np.random.default_rng(session.scenario.spec.seed + tick)
    shocks = rng.standard_normal((N_PATHS, STEPS))
    cascade_p = _cascade_probability(session)
    probs, fund, eta_sev, eta_fund = _project(session, shocks, cascade_p)
    before = eta_sev.prob_within_15
    before_fund = fund[-1].p50
    control_ids = list(dict.fromkeys(a.control_id for a in session.actions.values()
                                     if a.status == "proposed" and a.control_id))
    what_ifs = {}
    for cid in control_ids:
        alt_probs, alt_fund, alt_eta, _ = _project(session, shocks, cascade_p, cid)
        after = alt_eta.prob_within_15
        what_ifs[cid] = WhatIf(control_id=cid, p_sev1_15_before=before,
            p_sev1_15_after=after, fund_p50_15_before=before_fund,
            fund_p50_15_after=alt_fund[-1].p50,
            text=f"Simulated {cid}: SEV-1 ≤15m {before:.0%} → {after:.0%}; fund median {before_fund:.1f}% → {alt_fund[-1].p50:.1f}%.")
    values = session.frame.values
    drivers = [Driver(signal=code, contribution=weight, text=reason) for code, weight, reason in [
        ("INS_FUND_PCT", max(0, 100 - values["INS_FUND_PCT"]) / 100, "Insurance fund drawdown"),
        ("LIQ_RATE", min(values["LIQ_RATE"] / 500, 1), "Executed liquidations per minute"),
        ("PX_CHG_5M", min(abs(values["PX_CHG_5M"]) / 10, 1), "Recent price move"),
    ]]
    drivers.sort(key=lambda driver: driver.contribution, reverse=True)
    headline = (f"SEV-1 within 15 min: {before:.0%} in simulated paths"
                if before >= .1 else "Simulated escalation risk currently low")
    forecast = Forecast(computed_t=session.frame.t, horizon_min=list(HORIZONS),
        n_paths=N_PATHS, sev_probs=probs, eta_sev1_min=eta_sev, ins_fund=fund,
        eta_fund_25_min=eta_fund, drivers=drivers,
        cascade_model_p=cascade_p, headline=headline)
    return forecast, what_ifs
