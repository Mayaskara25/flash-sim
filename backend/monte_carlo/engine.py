"""Monte Carlo crash paths — stress tests, not forecasts."""

from __future__ import annotations

from typing import Any

import numpy as np

from liquidation.model import liquidation_price
from simulation.market import ASSETS, USD_INR, VOL_MULT


def run_monte_carlo(
    portfolio: dict[str, np.ndarray],
    n_sims: int,
    crash_severity: float,
    volatility: str,
    horizon_minutes: int,
    seed: int = 7,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    steps = max(20, min(horizon_minutes, 80))
    vol = 0.012 * VOL_MULT[volatility] * np.sqrt(max(horizon_minutes, 5) / 30.0)
    start = float(ASSETS["NVDA"]["start"])
    mu = -crash_severity / steps
    shocks = rng.normal(mu, vol, size=(n_sims, steps))
    log_paths = np.cumsum(shocks, axis=1)
    paths = start * np.exp(log_paths)
    paths = np.concatenate([np.full((n_sims, 1), start), paths], axis=1)
    finals = paths[:, -1]

    entry = portfolio["entry"]
    qty = portfolio["qty"]
    lev = portfolio["leverage"]
    is_long = portfolio["is_long"]
    asset = portfolio["asset"]
    betas = np.array([ASSETS[a]["beta"] for a in asset])
    liq = liquidation_price(entry, lev, is_long)

    nvda_ret = (finals - start) / start
    starts = np.array([ASSETS[a]["start"] for a in asset])
    # finals_asset[sim, pos] = starts[pos] * (1 + betas[pos] * nvda_ret[sim])
    asset_px = starts[None, :] * (1.0 + betas[None, :] * nvda_ret[:, None])
    asset_px = np.maximum(asset_px, 0.05 * starts[None, :])
    dist = np.where(
        is_long[None, :],
        (asset_px - liq[None, :]) / asset_px,
        (liq[None, :] - asset_px) / asset_px,
    )
    liquidated = dist <= 0
    liq_counts = liquidated.sum(axis=1)
    pnl = np.where(
        is_long[None, :],
        (asset_px - entry[None, :]) * qty[None, :],
        (entry[None, :] - asset_px) * qty[None, :],
    )
    losses = np.minimum(pnl, 0).sum(axis=1)  # negative
    loss_abs = -losses
    # Platform exposure: sum of |pnl| on liquidated + near
    dist_pct = dist * 100.0
    at_risk = dist_pct < 5.0
    exposure = (np.abs(pnl) * at_risk).sum(axis=1)

    severe_threshold = max(int(0.12 * len(entry)), 1)
    severe_freq = float(np.mean(liq_counts >= severe_threshold))

    # subsample paths for chart
    idx = np.linspace(0, n_sims - 1, num=min(80, n_sims), dtype=int)
    median_path = np.median(paths, axis=0)
    worst_i = int(np.argmin(finals))
    chart_paths = paths[idx].round(2).tolist()

    # histograms
    price_hist = _hist(finals, 24)
    liq_hist = _hist(liq_counts.astype(float), 20)
    loss_hist = _hist(loss_abs / 1e6, 20)
    exp_hist = _hist(exposure / 1e6, 20)

    return {
        "n_simulations": int(n_sims),
        "average_liquidations": round(float(np.mean(liq_counts)), 1),
        "median_liquidations": round(float(np.median(liq_counts)), 1),
        "worst_case_liquidations": int(np.max(liq_counts)),
        "average_exposure_usd": float(np.mean(exposure)),
        "max_exposure_usd": float(np.max(exposure)),
        "average_loss_usd": float(np.mean(loss_abs)),
        "severe_cascade_frequency": round(severe_freq, 4),
        "severe_threshold_liquidations": severe_threshold,
        "label": "Simulation frequency under model assumptions",
        "disclaimer": (
            "Monte Carlo simulation explores many possible market paths under specified assumptions. "
            "It is used here as a stress-testing tool, not as a guaranteed forecast."
        ),
        "paths_sample": chart_paths,
        "median_path": [round(float(x), 2) for x in median_path],
        "severe_path": [round(float(x), 2) for x in paths[worst_i]],
        "start_price": start,
        "price_hist": price_hist,
        "liquidation_hist": liq_hist,
        "loss_hist_usd_m": loss_hist,
        "exposure_hist_usd_m": exp_hist,
        "usd_inr": USD_INR,
        "horizon_minutes": horizon_minutes,
        "crash_severity": crash_severity,
        "volatility": volatility,
    }


def _hist(arr: np.ndarray, bins: int) -> dict[str, list]:
    counts, edges = np.histogram(arr, bins=bins)
    centers = ((edges[:-1] + edges[1:]) / 2).tolist()
    return {"centers": [round(float(c), 3) for c in centers], "counts": counts.astype(int).tolist()}
