"""Synthetic leveraged portfolio — not real user positions."""

from __future__ import annotations

import numpy as np

from liquidation.model import classify_status, distance_to_liquidation, liquidation_price, unrealized_pnl
from simulation.market import ASSETS, USD_INR

LEVERAGE_BUCKETS = np.array([5, 8, 10, 12, 15, 18, 20, 25])


def generate_portfolio(
    n_traders: int,
    avg_leverage: float,
    long_ratio: float,
    prices: dict[str, float],
    seed: int = 42,
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    symbols = list(ASSETS.keys())
    # Over-weight the crash beta names so clusters form
    weights = np.array([0.34, 0.22, 0.16, 0.14, 0.14], dtype=float)
    asset_idx = rng.choice(len(symbols), size=n_traders, p=weights)
    asset = np.array([symbols[i] for i in asset_idx])
    starts = np.array([ASSETS[s]["start"] for s in asset])
    currents = np.array([prices[s] for s in asset])

    is_long = rng.random(n_traders) < long_ratio
    # Leverage clustered around avg with discrete buckets
    bucket_p = np.exp(-0.35 * np.abs(LEVERAGE_BUCKETS - avg_leverage))
    bucket_p /= bucket_p.sum()
    leverage = rng.choice(LEVERAGE_BUCKETS, size=n_traders, p=bucket_p).astype(float)
    # Quantity: lognormal notional in USD
    notional_usd = rng.lognormal(mean=9.4, sigma=0.85, size=n_traders)  # ~12k median
    qty = np.maximum(notional_usd / starts, 1.0)
    entry = starts * (1.0 + rng.normal(0.0, 0.028, size=n_traders))
    entry = np.clip(entry, starts * 0.90, starts * 1.10)
    initial_margin_usd = (entry * qty) / leverage
    trader_id = np.array([f"TR{i:04d}" for i in range(1, n_traders + 1)])

    liq = liquidation_price(entry, leverage, is_long)
    pnl_usd = unrealized_pnl(currents, entry, qty, is_long)
    dist = distance_to_liquidation(currents, liq, is_long)
    status = classify_status(dist)
    pos_value_usd = currents * qty

    return {
        "trader_id": trader_id,
        "asset": asset,
        "is_long": is_long,
        "entry": entry,
        "current": currents,
        "qty": qty,
        "leverage": leverage,
        "margin_usd": initial_margin_usd,
        "pnl_usd": pnl_usd,
        "liq": liq,
        "distance_pct": dist,
        "status": status,
        "pos_value_usd": pos_value_usd,
    }


def summarize(pf: dict[str, np.ndarray]) -> dict:
    status = pf["status"]
    n = len(status)
    counts = {
        "total": int(n),
        "safe": int(np.sum(status == "SAFE")),
        "at_risk": int(np.sum(status == "AT RISK")),
        "near_liquidation": int(np.sum(status == "NEAR LIQUIDATION")),
        "liquidated": int(np.sum(status == "LIQUIDATED")),
    }
    lev_hist = {}
    for b in LEVERAGE_BUCKETS:
        lev_hist[str(int(b)) + "x"] = int(np.sum(pf["leverage"] == b))
    return {
        **counts,
        "positions_at_risk": counts["at_risk"] + counts["near_liquidation"] + counts["liquidated"],
        "avg_leverage": float(np.mean(pf["leverage"])),
        "long_pct": float(np.mean(pf["is_long"]) * 100),
        "short_pct": float((1.0 - np.mean(pf["is_long"])) * 100),
        "leverage_histogram": lev_hist,
        "usd_inr": USD_INR,
    }
