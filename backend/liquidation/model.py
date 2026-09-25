"""Modelled liquidation threshold — research simplification, not a proprietary engine."""

from __future__ import annotations

import numpy as np

# Fraction of initial margin that can be consumed before modelled liquidation.
# Distance from entry to modelled liquidation ≈ buffer / leverage.
# 20x ≈ 7.8% adverse move; 10x ≈ 15.5%. Research simplification only.
MAINTENANCE_BUFFER = 1.55
NEAR_LIQ_PCT = 1.5
AT_RISK_PCT = 5.0


def liquidation_price(entry: np.ndarray, leverage: np.ndarray, is_long: np.ndarray) -> np.ndarray:
    move = MAINTENANCE_BUFFER / leverage
    return np.where(is_long, entry * (1.0 - move), entry * (1.0 + move))


def distance_to_liquidation(current: np.ndarray, liq: np.ndarray, is_long: np.ndarray) -> np.ndarray:
    dist = np.where(is_long, (current - liq) / current, (liq - current) / current)
    return dist * 100.0


def classify_status(distance_pct: np.ndarray) -> np.ndarray:
    status = np.full(distance_pct.shape, "SAFE", dtype=object)
    status[distance_pct < AT_RISK_PCT] = "AT RISK"
    status[distance_pct < NEAR_LIQ_PCT] = "NEAR LIQUIDATION"
    status[distance_pct <= 0] = "LIQUIDATED"
    return status


def unrealized_pnl(current: np.ndarray, entry: np.ndarray, qty: np.ndarray, is_long: np.ndarray) -> np.ndarray:
    return np.where(is_long, (current - entry) * qty, (entry - current) * qty)
