"""Interpretable cascade-risk model trained on simulated research scenarios."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

FEATURE_NAMES = [
    "price_drop",
    "volatility",
    "volume_change",
    "average_leverage",
    "near_liquidation_ratio",
    "liquidation_ratio",
    "liquidation_concentration",
    "long_short_imbalance",
    "liquidity_score",
    "recent_liquidation_rate",
]


def _label(x: np.ndarray) -> np.ndarray:
    """Heuristic labels for synthetic training — not real market events."""
    score = (
        2.8 * x[:, 0]
        + 0.9 * x[:, 1]
        + 0.4 * np.clip(x[:, 2] / 4.0, 0, 1)
        + 1.1 * (x[:, 3] / 20.0)
        + 3.4 * x[:, 4]
        + 2.6 * x[:, 5]
        + 1.6 * x[:, 6]
        + 0.8 * x[:, 7]
        + 1.8 * (1.0 - x[:, 8])
        + 1.4 * x[:, 9]
    )
    return (score > 4.2).astype(int)


def train_model(seed: int = 42) -> LogisticRegression:
    rng = np.random.default_rng(seed)
    n = 2400
    x = np.column_stack(
        [
            rng.uniform(0, 0.25, n),
            rng.uniform(0.5, 2.2, n),
            rng.uniform(0, 8, n),
            rng.uniform(5, 25, n),
            rng.uniform(0, 0.45, n),
            rng.uniform(0, 0.35, n),
            rng.uniform(0.15, 0.95, n),
            rng.uniform(0, 0.8, n),
            rng.uniform(0.3, 1.0, n),
            rng.uniform(0, 0.4, n),
        ]
    )
    y = _label(x)
    clf = LogisticRegression(max_iter=400, C=1.4)
    clf.fit(x, y)
    return clf


_MODEL = train_model()


def interpretable_score(features: dict[str, float]) -> float:
    s = (
        22 * min(features["price_drop"] / 0.20, 1.0)
        + 8 * min((features["volatility"] - 0.5) / 1.5, 1.0)
        + 6 * min(features["volume_change"] / 5.0, 1.0)
        + 10 * min(features["average_leverage"] / 20.0, 1.0)
        + 18 * min(features["near_liquidation_ratio"] / 0.25, 1.0)
        + 12 * min(features["liquidation_ratio"] / 0.18, 1.0)
        + 8 * features["liquidation_concentration"]
        + 6 * features["long_short_imbalance"]
        + 6 * (1.0 - features["liquidity_score"])
        + 4 * min(features["recent_liquidation_rate"] / 0.2, 1.0)
    )
    return float(np.clip(s, 0, 100))


def classify(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 62:
        return "HIGH"
    if score >= 38:
        return "MEDIUM"
    return "LOW"


def evaluate(features: dict[str, float]) -> dict[str, Any]:
    x = np.array([[features[k] for k in FEATURE_NAMES]], dtype=float)
    proba = float(_MODEL.predict_proba(x)[0, 1])
    base = interpretable_score(features)
    blended = 0.62 * base + 0.38 * (proba * 100.0)
    score = round(float(np.clip(blended, 0, 100)))
    level = classify(score)
    reasons = _reasons(features, level)
    display = _feature_display(features)
    return {
        "cascade_risk_score": score,
        "classification": level,
        "model_note": "AI model trained/evaluated on simulated research scenarios.",
        "not_a_forecast": True,
        "features": display,
        "why": reasons,
        "raw_features": features,
        "sklearn_probability": round(proba, 4),
        "interpretable_score": round(base, 1),
    }


def _feature_display(f: dict[str, float]) -> dict[str, str]:
    def band(v: float, high: float, mid: float) -> str:
        if v >= high:
            return "High"
        if v >= mid:
            return "Moderate"
        return "Low"

    liq = "Low" if f["liquidity_score"] < 0.5 else ("Moderate" if f["liquidity_score"] < 0.85 else "Normal")
    return {
        "Price Shock": band(f["price_drop"], 0.10, 0.05),
        "Leverage Concentration": band(f["average_leverage"], 16, 12),
        "Near-Liquidation Positions": band(f["near_liquidation_ratio"], 0.12, 0.05),
        "Liquidity": liq,
        "Long Exposure Concentration": band(f["long_short_imbalance"], 0.45, 0.22),
        "Liquidation Clustering": band(f["liquidation_concentration"], 0.55, 0.35),
        "Volume Spike": band(f["volume_change"], 3.0, 1.5),
        "Recent Liquidation Rate": band(f["recent_liquidation_rate"], 0.12, 0.04),
    }


def _reasons(f: dict[str, float], level: str) -> str:
    bits = []
    if f["near_liquidation_ratio"] > 0.08:
        bits.append("a large share of synthetic positions is approaching modelled liquidation thresholds")
    if f["average_leverage"] > 14:
        bits.append("average leverage is elevated")
    if f["liquidity_score"] < 0.7:
        bits.append("liquidity is reduced")
    if f["long_short_imbalance"] > 0.35:
        bits.append("long-side exposure is concentrated")
    if f["price_drop"] > 0.07:
        bits.append("the simulated price shock is material")
    if f["liquidation_concentration"] > 0.5:
        bits.append("vulnerable positions are clustered in a small set of assets")
    if not bits:
        return "Current simulated conditions do not resemble historical-style cascade setups under this research model."
    lead = f"Cascade classification is {level} because "
    return lead + "; ".join(bits) + "."
