"""Simple anomaly flags on simulated liquidation activity."""

from __future__ import annotations

from typing import Any

import numpy as np


def detect_anomalies(
    summary: dict,
    exposure: dict,
    crash: float,
    liquidity: str,
    seed: int = 42,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    # Synthetic rolling baseline of liquidation counts under mild conditions
    baseline = rng.normal(loc=40, scale=18, size=60)
    baseline = np.clip(baseline, 0, None)
    current = float(summary["liquidated"])
    mu, sd = float(baseline.mean()), float(baseline.std() + 1e-6)
    z = (current - mu) / sd

    anomalies: list[dict[str, Any]] = []
    if z > 2.2:
        anomalies.append(
            {
                "severity": "HIGH" if z > 3 else "MEDIUM",
                "time": "T+sim",
                "asset": "BOOK",
                "code": "LIQ_SPIKE",
                "description": (
                    f"Liquidation volume is {z:.1f} standard deviations above the recent simulated baseline."
                ),
                "simulated": True,
            }
        )

    # Concentration: share of liquidations in top asset
    by_asset = exposure["by_asset"]
    liq_total = sum(a["liquidation_usd"] for a in by_asset) or 1.0
    top = max(by_asset, key=lambda a: a["liquidation_usd"]) if by_asset else None
    if top and top["liquidation_usd"] / liq_total > 0.45 and summary["liquidated"] > 20:
        anomalies.append(
            {
                "severity": "MEDIUM",
                "time": "T+sim",
                "asset": top["asset"],
                "code": "ASSET_CONCENTRATION",
                "description": (
                    f"Simulated liquidations are concentrated in {top['asset']} "
                    f"({100 * top['liquidation_usd'] / liq_total:.0f}% of liquidation exposure)."
                ),
                "simulated": True,
            }
        )

    if crash >= 0.12 and liquidity != "Normal":
        anomalies.append(
            {
                "severity": "HIGH",
                "time": "T+sim",
                "asset": "NVDA",
                "code": "CLUSTER_WINDOW",
                "description": "Large number of modelled liquidations occur within a short simulated window while liquidity is reduced.",
                "simulated": True,
            }
        )

    near = summary["near_liquidation"]
    n = summary["total"] or 1
    if near / n > 0.08:
        anomalies.append(
            {
                "severity": "MEDIUM",
                "time": "T+sim",
                "asset": "BOOK",
                "code": "LEVERAGE_CONCENTRATION",
                "description": "Unusual clustering of high-leverage synthetic positions within 1.25% of modelled liquidation.",
                "simulated": True,
            }
        )

    if summary["liquidated"] > 0 and crash < 0.03:
        anomalies.append(
            {
                "severity": "LOW",
                "time": "T+sim",
                "asset": "BOOK",
                "code": "PRICE_MISMATCH",
                "description": "Modelled liquidation count is non-zero despite a small simulated price move — review entry/leverage mix.",
                "simulated": True,
            }
        )

    if not anomalies:
        anomalies.append(
            {
                "severity": "INFO",
                "time": "T+sim",
                "asset": "BOOK",
                "code": "NONE",
                "description": "No abnormal liquidation pattern versus the simulated baseline.",
                "simulated": True,
            }
        )
    return anomalies
