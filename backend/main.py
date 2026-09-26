from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from incident.api import router as incident_router
from simulation.engine import ENGINE

app = FastAPI(
    title="P2 Risk Engine",
    description="Research simulation — public/historical market data + synthetic positions. Not a trading venue.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incident_router, prefix="/incident")


class SimParams(BaseModel):
    crash_magnitude: Optional[float] = Field(None, description="0–25 percent or 0–0.25 fraction")
    volatility: Optional[str] = None
    liquidity: Optional[str] = None
    n_traders: Optional[int] = Field(None, ge=1000, le=20000)
    avg_leverage: Optional[float] = Field(None, ge=3, le=30)
    long_ratio: Optional[float] = Field(None, ge=0.2, le=0.9)
    horizon_minutes: Optional[int] = None


class MonteCarloRequest(BaseModel):
    n_simulations: int = 1000
    crash_severity: Optional[float] = None
    volatility: Optional[str] = None
    time_horizon_minutes: Optional[int] = None


class DemoPhase(BaseModel):
    phase: int = 0


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "SIMULATION"}


@app.get("/data-status")
def data_status() -> dict[str, str]:
    return ENGINE.data_status()


@app.get("/simulation/params")
def get_params() -> dict[str, Any]:
    return ENGINE.public_params()


@app.post("/simulation/run")
def simulation_run(body: SimParams) -> dict[str, Any]:
    ENGINE.update(**body.model_dump())
    return ENGINE.overview()


@app.post("/simulation/reset")
def simulation_reset() -> dict[str, Any]:
    ENGINE.reset()
    return ENGINE.overview()


@app.post("/simulation/demo")
def simulation_demo(body: DemoPhase) -> dict[str, Any]:
    ENGINE.set_demo_phase(body.phase)
    return ENGINE.overview()


@app.get("/market-state")
def market_state() -> dict[str, Any]:
    return ENGINE.market()


@app.get("/overview")
def overview() -> dict[str, Any]:
    return ENGINE.overview()


@app.get("/positions")
def positions(
    page: int = 1,
    page_size: int = 40,
    asset: Optional[str] = None,
    side: Optional[str] = None,
    status: Optional[str] = None,
    leverage_min: Optional[float] = None,
    leverage_max: Optional[float] = None,
    distance_max: Optional[float] = None,
) -> dict[str, Any]:
    return ENGINE.positions_page(
        page=page,
        page_size=page_size,
        asset=asset,
        side=side,
        status=status,
        leverage_min=leverage_min,
        leverage_max=leverage_max,
        distance_max=distance_max,
    )


@app.get("/liquidations")
def liquidations() -> dict[str, Any]:
    s = ENGINE.summary()
    return {**s, "histogram": s["leverage_histogram"]}


@app.get("/exposure")
def exposure() -> dict[str, Any]:
    return ENGINE.exposure()


@app.post("/monte-carlo/run")
def monte_carlo_run(body: MonteCarloRequest) -> dict[str, Any]:
    return ENGINE.monte_carlo(
        n_sims=body.n_simulations,
        crash=body.crash_severity,
        vol=body.volatility,
        horizon=body.time_horizon_minutes,
    )


@app.get("/monte-carlo")
def monte_carlo_get(
    n_simulations: int = Query(1000),
    crash_severity: Optional[float] = None,
    volatility: Optional[str] = None,
    time_horizon_minutes: Optional[int] = None,
) -> dict[str, Any]:
    return ENGINE.monte_carlo(n_simulations, crash_severity, volatility, time_horizon_minutes)


@app.post("/cascade-risk")
def cascade_risk_post() -> dict[str, Any]:
    return ENGINE.cascade()


@app.get("/cascade-risk")
def cascade_risk_get() -> dict[str, Any]:
    return ENGINE.cascade()


@app.get("/anomalies")
def anomalies() -> dict[str, Any]:
    return {"items": ENGINE.anomalies(), "simulated": True}


@app.get("/risk-summary")
def risk_summary() -> dict[str, Any]:
    return ENGINE.risk_summary()
