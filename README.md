# Flash-Crash Console

Round 2, Track 3: a one-screen incident simulator for MochaTrade's Incident Commander, Tech Lead, and Comms/Support lead. It replays six compound scenarios with a synthetic leveraged book, classifies market versus system causes, proposes protective actions, prepares human-approved messages, and records the response in an incident log and summary. A seeded, labelled simulation projects severity, insurance-fund runway, and control what-ifs.

**Run locally:** install `backend/requirements.txt` and `frontend/` packages once, then launch `./start.sh` on Linux/macOS or `./start.ps1` on Windows. Open `http://127.0.0.1:5173/`. The live console is `/`; the seven earlier research views remain under `/analyst/*`. Add `?mock=1` only to inspect sample fixtures. For a timed operator walkthrough and recovery steps, use [the demo run sheet](docs/DEMO.md).

```text
Scenario JSON → 2 s clock → synthetic book + signals → classifier / severity / tags
                                                    ↓
                               forecast ← session → playbooks / controls / templates
                                                    ↓
                                    append-only log → summary → React console
```

The price paths, thresholds, book positions, fund, forecast distributions, and control effects are **prototype assumptions**, not MochaTrade production data. The app sends no customer messages and executes no trades. The forecasts describe this simulation, not future market prices. See the console's **Assumptions** panel and [the scenario spec](docs/SPEC.md).

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
