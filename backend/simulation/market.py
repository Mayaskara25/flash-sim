"""Public/historical-style sample market paths (deterministic, labelled as sample)."""

from __future__ import annotations

from typing import Any

import numpy as np

ASSETS: dict[str, dict[str, float]] = {
    "NVDA": {"start": 155.20, "beta": 1.00, "base_vol": 0.018},
    "TSLA": {"start": 248.10, "beta": 1.18, "base_vol": 0.024},
    "AAPL": {"start": 228.40, "beta": 0.72, "base_vol": 0.012},
    "MSFT": {"start": 415.60, "beta": 0.78, "base_vol": 0.013},
    "AMZN": {"start": 186.90, "beta": 0.90, "base_vol": 0.016},
}

VOL_MULT = {"Low": 0.7, "Medium": 1.0, "High": 1.85}
LIQ_MULT = {"Normal": 1.0, "Reduced": 0.62, "Severely Reduced": 0.38}
USD_INR = 83.50  # labelled synthetic conversion for INR exposure display


def current_prices(crash_magnitude: float) -> dict[str, float]:
    """crash_magnitude is 0–0.25 (fraction)."""
    return {
        symbol: round(meta["start"] * (1.0 - crash_magnitude * meta["beta"]), 2)
        for symbol, meta in ASSETS.items()
    }


def market_snapshot(
    crash_magnitude: float,
    volatility: str,
    liquidity: str,
    horizon_minutes: int,
    seed: int = 42,
) -> dict[str, Any]:
    prices = current_prices(crash_magnitude)
    nvda_start = ASSETS["NVDA"]["start"]
    nvda_px = prices["NVDA"]
    change = (nvda_px - nvda_start) / nvda_start
    vol_x = VOL_MULT[volatility]
    liq_x = LIQ_MULT[liquidity]
    volume_x = 1.0 + abs(change) * 16.0 * vol_x / max(liq_x, 0.25)
    candles = price_path(
        start=nvda_start,
        end=nvda_px,
        n=max(40, horizon_minutes),
        vol=ASSETS["NVDA"]["base_vol"] * vol_x,
        seed=seed,
    )
    severity = "NORMAL"
    if crash_magnitude >= 0.18:
        severity = "SEVERE"
    elif crash_magnitude >= 0.10:
        severity = "STRESSED"
    elif crash_magnitude >= 0.04:
        severity = "ELEVATED"

    crash_mode = crash_magnitude >= 0.04
    return {
        "primary_asset": "NVDA",
        "current_price": nvda_px,
        "starting_price": nvda_start,
        "price_change_pct": round(change * 100, 2),
        "volume": round(1_240_000 * volume_x),
        "volume_change_pct": round((volume_x - 1.0) * 100, 1),
        "volatility": volatility,
        "volatility_vs_baseline": round(vol_x * (1.0 + abs(change) * 4.0), 2),
        "liquidity": liquidity,
        "liquidity_score": liq_x,
        "crash_severity": severity,
        "crash_mode": crash_mode,
        "market_state": severity,
        "horizon_minutes": horizon_minutes,
        "candles": candles,
        "asset_prices": prices,
        "usd_inr": USD_INR,
        "data_label": "Historical/public sample series + simulated crash overlay",
    }


def price_path(start: float, end: float, n: int, vol: float, seed: int) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, 1.0, n)
    drift = start + (end - start) * t
    noise = rng.normal(0.0, vol * start, size=n)
    noise[0] = 0.0
    noise = np.cumsum(noise - noise.mean())
    noise *= 0.35
    close = np.maximum(drift + noise, 0.15 * start)
    close[-1] = end
    close[0] = start
    opens = np.concatenate([[start], close[:-1]])
    high = np.maximum(opens, close) * (1.0 + np.abs(rng.normal(0, vol * 0.35, n)))
    low = np.minimum(opens, close) * (1.0 - np.abs(rng.normal(0, vol * 0.35, n)))
    out = []
    for i in range(n):
        out.append(
            {
                "t": i,
                "open": round(float(opens[i]), 2),
                "high": round(float(high[i]), 2),
                "low": round(float(low[i]), 2),
                "close": round(float(close[i]), 2),
            }
        )
    return out
