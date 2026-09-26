"""Global simulation state — deterministic, shared across all endpoints."""

from __future__ import annotations

from typing import Any

import numpy as np

from anomaly_detection.detect import detect_anomalies
from cascade_model.model import evaluate as eval_cascade
from exposure.calc import compute_exposure
from monte_carlo.engine import run_monte_carlo
from simulation.market import LIQ_MULT, VOL_MULT, current_prices, market_snapshot
from simulation.portfolio import generate_portfolio, summarize

DEFAULTS = {
    "crash_magnitude": 0.08,
    "volatility": "High",
    "liquidity": "Reduced",
    "n_traders": 10000,
    "avg_leverage": 14.7,
    "long_ratio": 0.72,
    "horizon_minutes": 30,
    "seed": 42,
}


class SimulationEngine:
    def __init__(self) -> None:
        self.params = dict(DEFAULTS)
        self._pf: dict[str, np.ndarray] | None = None
        self._mc_cache: dict[str, Any] | None = None
        self.rebuild()

    def rebuild(self) -> None:
        p = self.params
        prices = current_prices(p["crash_magnitude"])
        self._pf = generate_portfolio(
            n_traders=int(p["n_traders"]),
            avg_leverage=float(p["avg_leverage"]),
            long_ratio=float(p["long_ratio"]),
            prices=prices,
            seed=int(p["seed"]),
        )
        self._mc_cache = None

    def update(self, **kwargs: Any) -> None:
        changed = False
        for k, v in kwargs.items():
            if v is None:
                continue
            if k == "crash_magnitude" and v > 1:
                v = v / 100.0
            if self.params.get(k) != v:
                self.params[k] = v
                changed = True
        if changed:
            self.rebuild()

    def reset(self) -> None:
        self.params = dict(DEFAULTS)
        self.rebuild()

    def set_demo_phase(self, phase: int) -> None:
        """phase 0–6 for the 1–2 minute crash story."""
        table = [
            dict(crash_magnitude=0.0, volatility="Low", liquidity="Normal", horizon_minutes=15),
            dict(crash_magnitude=0.03, volatility="Medium", liquidity="Normal", horizon_minutes=15),
            dict(crash_magnitude=0.06, volatility="Medium", liquidity="Reduced", horizon_minutes=30),
            dict(crash_magnitude=0.10, volatility="High", liquidity="Reduced", horizon_minutes=30),
            dict(crash_magnitude=0.14, volatility="High", liquidity="Reduced", horizon_minutes=30),
            dict(crash_magnitude=0.18, volatility="High", liquidity="Severely Reduced", horizon_minutes=60),
            dict(crash_magnitude=0.22, volatility="High", liquidity="Severely Reduced", horizon_minutes=60),
        ]
        phase = max(0, min(phase, len(table) - 1))
        self.update(**table[phase])

    def market(self) -> dict[str, Any]:
        p = self.params
        snap = market_snapshot(
            crash_magnitude=p["crash_magnitude"],
            volatility=p["volatility"],
            liquidity=p["liquidity"],
            horizon_minutes=int(p["horizon_minutes"]),
            seed=int(p["seed"]),
        )
        return snap

    def summary(self) -> dict[str, Any]:
        assert self._pf is not None
        return summarize(self._pf)

    def positions_page(
        self,
        page: int = 1,
        page_size: int = 40,
        asset: str | None = None,
        side: str | None = None,
        status: str | None = None,
        leverage_min: float | None = None,
        leverage_max: float | None = None,
        distance_max: float | None = None,
    ) -> dict[str, Any]:
        assert self._pf is not None
        pf = self._pf
        n = len(pf["trader_id"])
        mask = np.ones(n, dtype=bool)
        if asset:
            mask &= pf["asset"] == asset
        if side == "LONG":
            mask &= pf["is_long"]
        elif side == "SHORT":
            mask &= ~pf["is_long"]
        if status:
            mask &= pf["status"] == status
        if leverage_min is not None:
            mask &= pf["leverage"] >= leverage_min
        if leverage_max is not None:
            mask &= pf["leverage"] <= leverage_max
        if distance_max is not None:
            mask &= pf["distance_pct"] <= distance_max

        idx = np.where(mask)[0]
        # Show most stressed first
        order = idx[np.argsort(pf["distance_pct"][idx])]
        total = int(len(order))
        start = max(0, (page - 1) * page_size)
        sl = order[start : start + page_size]
        rows = []
        for i in sl:
            rows.append(
                {
                    "trader_id": str(pf["trader_id"][i]),
                    "asset": str(pf["asset"][i]),
                    "side": "LONG" if bool(pf["is_long"][i]) else "SHORT",
                    "entry_price": round(float(pf["entry"][i]), 2),
                    "current_price": round(float(pf["current"][i]), 2),
                    "quantity": round(float(pf["qty"][i]), 2),
                    "leverage": int(pf["leverage"][i]),
                    "initial_margin_usd": round(float(pf["margin_usd"][i]), 2),
                    "unrealized_pnl_usd": round(float(pf["pnl_usd"][i]), 2),
                    "liquidation_price": round(float(pf["liq"][i]), 2),
                    "distance_to_liquidation_pct": round(float(pf["distance_pct"][i]), 2),
                    "status": str(pf["status"][i]),
                }
            )
        return {
            "rows": rows,
            "total_filtered": total,
            "page": page,
            "page_size": page_size,
            "book_size": n,
            "model_label": "Modelled liquidation threshold",
        }

    def cascade_features(self) -> dict[str, float]:
        assert self._pf is not None
        pf = self._pf
        p = self.params
        market = self.market()
        status = pf["status"]
        n = max(len(status), 1)
        near = np.sum(status == "NEAR LIQUIDATION") / n
        liq = np.sum(status == "LIQUIDATED") / n
        long_share = float(np.mean(pf["is_long"]))
        imbalance = abs(2 * long_share - 1.0)
        # concentration of near+liq notional by asset
        stressed = np.isin(status, ["NEAR LIQUIDATION", "LIQUIDATED"])
        val = pf["pos_value_usd"]
        if stressed.any():
            assets = pf["asset"][stressed]
            v = val[stressed]
            shares = []
            for a in np.unique(assets):
                shares.append(float(v[assets == a].sum()) / float(v.sum()))
            herfindahl = float(sum(s * s for s in shares))
        else:
            herfindahl = 0.2
        return {
            "price_drop": abs(market["price_change_pct"]) / 100.0,
            "volatility": float(VOL_MULT[p["volatility"]]),
            "volume_change": abs(market["volume_change_pct"]) / 100.0,
            "average_leverage": float(np.mean(pf["leverage"])),
            "near_liquidation_ratio": float(near),
            "liquidation_ratio": float(liq),
            "liquidation_concentration": herfindahl,
            "long_short_imbalance": float(imbalance),
            "liquidity_score": float(LIQ_MULT[p["liquidity"]]),
            "recent_liquidation_rate": float(liq),
        }

    def cascade(self) -> dict[str, Any]:
        feat = self.cascade_features()
        result = eval_cascade(feat)
        result["stages"] = self.cascade_stages()
        return result

    def cascade_stages(self) -> list[dict[str, Any]]:
        assert self._pf is not None
        pf = self._pf
        s = summarize(pf)
        exp = compute_exposure(pf)
        crash = self.params["crash_magnitude"]
        n = s["total"]
        vulnerable = int(np.sum(pf["leverage"] >= 15))
        first_liq = s["liquidated"]
        more = s["near_liquidation"]
        contrib = lambda c: round(100 * c / max(n, 1), 2)
        return [
            {
                "id": "price_drop",
                "title": "MARKET PRICE DROP",
                "positions": n,
                "exposure_usd": exp["total_usd"],
                "risk_contribution": round(min(crash / 0.25, 1) * 18, 1),
                "detail": f"Simulated primary-asset decline of {crash * 100:.1f}%.",
            },
            {
                "id": "vulnerable",
                "title": "HIGH-LEVERAGE POSITIONS BECOME VULNERABLE",
                "positions": vulnerable,
                "exposure_usd": float(pf["pos_value_usd"][pf["leverage"] >= 15].sum()),
                "risk_contribution": contrib(vulnerable) * 0.4,
                "detail": "Synthetic book slice with leverage ≥ 15x.",
            },
            {
                "id": "first_liq",
                "title": "FIRST LIQUIDATIONS",
                "positions": first_liq,
                "exposure_usd": exp["liquidation_usd"],
                "risk_contribution": contrib(first_liq) * 1.2,
                "detail": "Positions past the modelled liquidation threshold.",
            },
            {
                "id": "selling",
                "title": "ADDITIONAL SELLING PRESSURE",
                "positions": s["at_risk"],
                "exposure_usd": exp["at_risk_usd"],
                "risk_contribution": 12 if crash > 0.08 else 5,
                "detail": "At-risk inventory that can add simulated market impact.",
            },
            {
                "id": "more",
                "title": "MORE POSITIONS APPROACH LIQUIDATION",
                "positions": more,
                "exposure_usd": exp["approaching_liq_usd"],
                "risk_contribution": contrib(more) * 1.5,
                "detail": "Distance to modelled liquidation < 1.5%.",
            },
            {
                "id": "cascade",
                "title": "POTENTIAL CASCADE",
                "positions": first_liq + more,
                "exposure_usd": exp["liquidation_usd"] + exp["approaching_liq_usd"],
                "risk_contribution": min(40.0, (first_liq + more) / max(n, 1) * 100),
                "detail": "Cluster of modelled liquidations plus near-threshold names — indicator only.",
            },
        ]

    def exposure(self) -> dict[str, Any]:
        assert self._pf is not None
        return compute_exposure(self._pf)

    def anomalies(self) -> list[dict[str, Any]]:
        return detect_anomalies(
            self.summary(),
            self.exposure(),
            self.params["crash_magnitude"],
            self.params["liquidity"],
            seed=int(self.params["seed"]),
        )

    def monte_carlo(self, n_sims: int | None = None, crash: float | None = None, vol: str | None = None, horizon: int | None = None) -> dict[str, Any]:
        assert self._pf is not None
        p = self.params
        n_sims = int(n_sims or 1000)
        crash = float(p["crash_magnitude"] if crash is None else crash)
        if crash > 1:
            crash /= 100.0
        vol = vol or p["volatility"]
        horizon = int(horizon or p["horizon_minutes"])
        key = f"{n_sims}-{crash}-{vol}-{horizon}-{p['n_traders']}-{p['avg_leverage']}-{p['long_ratio']}"
        if self._mc_cache and self._mc_cache.get("_key") == key:
            return self._mc_cache["data"]
        data = run_monte_carlo(self._pf, n_sims, crash, vol, horizon, seed=int(p["seed"]) + 7)
        self._mc_cache = {"_key": key, "data": data}
        return data

    def overview(self) -> dict[str, Any]:
        market = self.market()
        s = self.summary()
        cascade = self.cascade()
        return {
            "market": market,
            "kpis": {
                "current_price": market["current_price"],
                "price_change_pct": market["price_change_pct"],
                "volatility": market["volatility"],
                "volume_change_pct": market["volume_change_pct"],
                "total_positions": s["total"],
                "positions_at_risk": s["positions_at_risk"],
                "estimated_liquidations": s["liquidated"],
                "cascade_risk": cascade["cascade_risk_score"],
            },
            "simulated": True,
            "params": self.public_params(),
        }

    def risk_summary(self) -> dict[str, Any]:
        cascade = self.cascade()
        s = self.summary()
        mc = self.monte_carlo(n_sims=1000)
        level = cascade["classification"]
        reasons = []
        if s["avg_leverage"] > 13:
            reasons.append("High leverage concentration")
        if s["near_liquidation"] > 80:
            reasons.append("Large number of positions near liquidation")
        if self.params["liquidity"] != "Normal":
            reasons.append("Reduced liquidity")
        if s["long_pct"] > 60:
            reasons.append("High long-side concentration")
        if cascade["raw_features"]["liquidation_concentration"] > 0.4:
            reasons.append("Elevated liquidation clustering")
        if mc["severe_cascade_frequency"] > 0.08:
            reasons.append("Monte Carlo severe-scenario frequency elevated")
        actions = [
            "Increase monitoring frequency",
            "Review new high-leverage position limits",
            "Review margin requirements",
            "Alert risk-management team",
            "Monitor liquidity conditions",
            "Stress-test additional crash scenarios",
        ]
        return {
            "current_risk_level": level,
            "cascade_score": cascade["cascade_risk_score"],
            "reasons": reasons or ["Simulated book is within ordinary research-model bounds."],
            "proposed_actions": actions,
            "actions_label": "Proposed risk-management actions",
            "not_live_controls": True,
            "why": cascade["why"],
            "severe_mc_frequency": mc["severe_cascade_frequency"],
        }

    def public_params(self) -> dict[str, Any]:
        p = self.params
        return {
            "crash_magnitude": p["crash_magnitude"],
            "crash_pct": round(p["crash_magnitude"] * 100, 1),
            "volatility": p["volatility"],
            "liquidity": p["liquidity"],
            "n_traders": p["n_traders"],
            "avg_leverage": p["avg_leverage"],
            "long_ratio": p["long_ratio"],
            "long_pct": round(p["long_ratio"] * 100, 1),
            "short_pct": round((1 - p["long_ratio"]) * 100, 1),
            "horizon_minutes": p["horizon_minutes"],
        }

    def data_status(self) -> dict[str, str]:
        return {
            "market_data": "Historical/Public (sample series)",
            "trader_positions": "Synthetic",
            "crash": "Simulated",
            "monte_carlo": "Simulated",
            "ai_model": "Research prototype",
        }


ENGINE = SimulationEngine()
