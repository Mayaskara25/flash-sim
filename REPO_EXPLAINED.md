# P2 Risk Engine — Repo Explained

## 1. What it is

**P2 Risk Engine — Market Crash & Liquidation Intelligence** (`README.md:1-7`, `backend/main.py:11-15`).

A local research-simulation dashboard for leveraged-book crash risk:
- Synthetic book of 1,000–20,000 traders over 5 assets: NVDA, TSLA, AAPL, MSFT, AMZN (`backend/simulation/market.py`, `backend/simulation/portfolio.py`).
- Global simulation controls (crash %, volatility, liquidity, trader count, leverage, long/short mix) rebuild the book and update every view (`README.md:44`).
- 7 pages: Overview, Market Crash, Liquidation Monitor, Cascade Risk, Monte Carlo, Exposure, Risk Response (`frontend/src/App.tsx`, `frontend/src/pages/`).
- FastAPI backend (port 8000) + React + TypeScript + Tailwind + Recharts frontend (port 5173, `/api` proxied) (`frontend/vite.config.ts`, `frontend/package.json`).
- Deterministic/seeding (`seed 42`) so runs are reproducible.

## 2. What it is not

Explicitly **not** (`README.md:5`, `backend/main.py:13`):

- Not a trading platform. Executes no trades, places no orders.
- Not a live exchange feed. No real user positions, no real margin engine.
- Not a forecast. Cascade score and Monte Carlo outputs are labelled `not_a_forecast`, `simulated: True`, `disclaimer`.
- No auth / users / DB / persistence. Open local API, CORS limited to `localhost:5173` (`backend/main.py:17-23`). In-memory singleton `ENGINE` resets on restart (`backend/simulation/engine.py`).
- No tests, no prod build config, no Linux launcher (only `start.ps1`, Windows-only).

## 3. Real vs stub / synthetic

No `TODO / FIXME / stub / mock / placeholder / pass` stubs in `backend/` or `frontend/src/`. Everything wired is functional. The only non-real file is boilerplate docs.

| Area | Status | Evidence |
|---|---|---|
| `backend/main.py` — 14 routes (`/health`, `/data-status`, `/overview`, `/positions`, `/liquidations`, `/exposure`, `/monte-carlo`, `/cascade-risk`, `/anomalies`, `/risk-summary`, `/simulation/run\|reset\|demo`) | **Real** | All delegate to live `ENGINE` |
| `backend/simulation/engine.py` (371 lines) — rebuild/update/reset/demo/market/summary/cascade/exposure/anomalies/monte-carlo | **Real**, core singleton | `ENGINE=SimulationEngine()` |
| `backend/simulation/portfolio.py` — synthetic book generator | **Real but synthetic-by-design** | Asset weights `[0.34,0.22,0.16,0.14,0.14]`, leverage buckets `[5,8,10,12,15,18,20,25]`, `lognormal(9.4,0.85)` notional |
| `backend/simulation/market.py` — prices / paths | **Real but synthetic-by-design + hardcoded** | Start prices NVDA 155.20, TSLA 248.10, etc.; `VOL_MULT`, `LIQ_MULT`, `USD_INR=83.5`; labelled “simulated crash overlay” |
| `backend/liquidation/model.py` (34 lines) | **Real, intentionally simplified** | `liq = entry*(1∓1.55/lev)`; docstring: “not a proprietary engine” (`backend/liquidation/model.py:1`) |
| `backend/cascade_model/model.py` (153 lines) | **Real research prototype, trained on fake data** | `train_model(seed=42)` on `n=2400` uniform synthetic rows + heuristic `_label(score>4.2)`; “not real market events” (`backend/cascade_model/model.py:25`); `LogisticRegression(max_iter=400,C=1.4)` trained at import; `blended=0.62*base+0.38*proba*100`; `>=80 CRITICAL, >=62 HIGH, >=38 MEDIUM` |
| `backend/monte_carlo/engine.py` (112 lines) | **Real stress-tester** | GBM-ish shocks, `steps=clamp(horizon,20,80)`, vectorized `[n_sims x n_pos]`, samples 80 paths + median + worst |
| `backend/exposure/calc.py` (66 lines) | **Real** | Pure numpy sums: total/long/short/net/gross, by-leverage, by-asset |
| `backend/anomaly_detection/detect.py` (108 lines) | **Real rule-based** | Seeded `baseline=N(40,18,60)`, `z>2.2` spike, `>45%` concentration, etc.; all `simulated=True` |
| `frontend/src/services/api.ts` (52 lines) | **Real** | Covers all backend routes, `BASE=/api` |
| `frontend/src/context/SimContext.tsx` (155 lines) | **Real** | Global sim state + 7-phase demo timer (`14s x 7`) |
| `frontend/src/components/` (`Layout`, `SimControls`, `DataStatus`, `PriceChart`, `KpiCard`) | **Real** | Nav, sliders (crash 0–25%, lev 5–22x), `/data-status` panel |
| `frontend/src/pages/` (7 pages) | **Real** | Fetch on `revision`, Recharts, paginated `LiquidationMonitor` (`page_size 25`), `RiskResponse` marked “not live controls” |
| `frontend/README.md` | **Stub / boilerplate — ignore** | Unedited Vite template about `plugin-react`, `React Compiler`, `oxlint`; not app-specific |

## 4. Synthetic-by-design (not bugs)

Hardcoded because it is a simulation, all labelled in code/UI:

- Start prices, betas, `FX=83.5`, volume/liquidity multipliers (`backend/simulation/market.py`, `frontend/src/services/format.ts`).
- Demo phase table 0–6 in `engine.set_demo_phase`.
- Anomaly baseline distribution, Monte Carlo cache key.
- `TR0001…` position IDs, entry `= start*(1+N(0,0.028))` clipped 0.9–1.1x.

## 5. What is missing (if you expected it)

- No live market connector, no broker/exchange integration.
- No proprietary liquidation engine replica — formula is `buffer/leverage`.
- No ML on real data — cascade model trains on synthetic uniform data at import.
- No persistence, no auth, no multi-user, no tests.
- `start.ps1:3-5` assumes `.venv` + `node_modules` already exist; no build/checks.

## 6. Run it

```powershell
# Terminal 1 — API
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — UI
cd frontend
npm install
npm run dev
# open http://localhost:5173
# or: .\start.ps1 (Windows only, assumes .venv + node_modules exist)
```

Linux API equivalent: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload --port 8000`.
