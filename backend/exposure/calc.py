"""Exposure aggregates on the synthetic book."""

from __future__ import annotations

from typing import Any

import numpy as np

from simulation.market import ASSETS, USD_INR


def compute_exposure(pf: dict[str, np.ndarray]) -> dict[str, Any]:
    value = pf["pos_value_usd"]
    is_long = pf["is_long"]
    status = pf["status"]
    lev = pf["leverage"]
    asset = pf["asset"]
    pnl = pf["pnl_usd"]

    long_exp = float(value[is_long].sum())
    short_exp = float(value[~is_long].sum())
    liq_mask = status == "LIQUIDATED"
    near_mask = status == "NEAR LIQUIDATION"
    risk_mask = np.isin(status, ["AT RISK", "NEAR LIQUIDATION", "LIQUIDATED"])
    liq_exp = float(value[liq_mask].sum())
    near_exp = float(value[near_mask | (status == "AT RISK")].sum())
    est_loss = float(-np.minimum(pnl[liq_mask], 0).sum())

    by_lev: dict[str, float] = {}
    for b in sorted(set(lev.tolist())):
        by_lev[f"{int(b)}x"] = float(value[lev == b].sum())

    by_asset = []
    for symbol in ASSETS:
        m = asset == symbol
        if not np.any(m):
            continue
        le = float(value[m & is_long].sum())
        se = float(value[m & ~is_long].sum())
        by_asset.append(
            {
                "asset": symbol,
                "long_usd": le,
                "short_usd": se,
                "net_usd": le - se,
                "at_risk_usd": float(value[m & risk_mask].sum()),
                "liquidation_usd": float(value[m & liq_mask].sum()),
            }
        )

    approaching = float(value[near_mask].sum())

    return {
        "total_usd": float(value.sum()),
        "long_usd": long_exp,
        "short_usd": short_exp,
        "net_usd": long_exp - short_exp,
        "gross_usd": long_exp + short_exp,
        "liquidation_usd": liq_exp,
        "at_risk_usd": near_exp,
        "approaching_liq_usd": approaching,
        "estimated_loss_usd": est_loss,
        "by_leverage": by_lev,
        "by_asset": by_asset,
        "usd_inr": USD_INR,
    }
