# P2 Risk Engine — Market Crash & Liquidation Intelligence

> **Round 2 build (Track 3: Flash-Crash Simulation):** start at [`docs/PLAN.md`](docs/PLAN.md). Contracts: [`docs/CONTRACTS.md`](docs/CONTRACTS.md) · Work packages: [`docs/handoffs/`](docs/handoffs/README.md) · Spec: [`docs/SPEC.md`](docs/SPEC.md)

Research simulation for leveraged-book risk: crash monitoring, synthetic liquidation clusters, cascade scoring, Monte Carlo stress tests, and exposure.

This is **not** a trading platform. It does **not** execute trades or use real user positions.

**Research Simulation — Public/Historical Market Data + Synthetic Positions**

## Run locally

Terminal 1 — API:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Terminal 2 — UI:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

The Vite dev server proxies `/api` to FastAPI on port 8000.

## Architecture

- `frontend/` React + TypeScript + Tailwind + Recharts
- `backend/` FastAPI, NumPy, scikit-learn
  - `simulation/` market path + synthetic book
  - `liquidation/` modelled threshold (not a proprietary engine)
  - `cascade_model/` logistic model trained on simulated scenarios
  - `monte_carlo/` path ensemble stress tests
  - `exposure/` book aggregates
  - `anomaly_detection/` z-score / concentration flags

Simulation parameters are global: changing crash, volatility, liquidity, trader count, leverage, or long/short mix rebuilds the book and updates every view.
