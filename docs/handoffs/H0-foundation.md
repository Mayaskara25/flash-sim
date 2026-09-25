# H0: Foundation (contracts, stubs, fixtures, CI)

| | |
|---|---|
| Branch | `h0-foundation` |
| Owner | A |
| Size | S |
| Depends on | — |
| Blocks | everything |

## Goal
Turn `docs/CONTRACTS.md` into code and a stubbed API, so that backend and frontend work can start in parallel against the same shapes on day one.

## Read first
PLAN §3–6, CONTRACTS (all), `REPO_EXPLAINED.md`.

## You own
- `backend/incident/__init__.py`, `backend/incident/contracts.py`, `backend/incident/catalogue.py` (signal table only), `backend/incident/api.py` (stub router)
- `backend/main.py` (only: `app.include_router(incident_router, prefix="/incident")`)
- `backend/requirements.txt` (add `pytest`, `httpx`), `backend/pytest.ini`, `backend/tests/__init__.py`, `backend/tests/test_contract_fixtures.py`, `backend/tests/test_stub_api.py`
- `docs/contracts/fixtures/*.json`
- `frontend/src/incident/types.ts`, `frontend/src/incident/api.ts`, `frontend/src/incident/fixtures.ts` (imports the JSON fixtures)
- `frontend/vite.config.ts` (only if needed to import fixtures from `../docs`; otherwise copy them to `frontend/src/incident/fixtures/` via a script)
- `start.sh` (Linux/macOS equivalent of `start.ps1`)
- `.github/workflows/ci.yml`, `.github/pull_request_template.md`

## Tasks
- [ ] `contracts.py`: pydantic v2 models for everything in CONTRACTS §1, §5–7 (enums as `Literal`), plus the `SignalFrame`, `Effect` and `ControlDef` dataclasses from §3–4.
- [ ] `catalogue.py`: the CONTRACTS §2 table as `SIGNALS: list[SignalDef]` and a `status_of(code, value) -> SignalStatus` helper (rule: for `up`, value ≥ threshold; for `down`, value ≤ threshold; missing thresholds are skipped).
- [ ] Hand-write 7 state fixtures + `summary_c1.json` that tell the C1 story (SPEC §12.2): idle → normal (T-01:00) → warning (T+02:10, tags M1) → critical (T+14:32, tags M1 I1 M2, reduce-only proposed with a what-if) → emergency (a variant with the fund at 22%, to exercise UI colours) → stabilising (T+40:10, pending stepdown) → resolved (T+55:00). Use realistic numbers from SPEC. Include `forecast` in critical/emergency so the H9 UI can be built early.
- [ ] `api.py` stub: every endpoint in CONTRACTS §7 exists. `GET /state` returns the current fixture. `POST /start` moves to `normal`. Other POSTs return the "next" fixture so the frontend can click through. Mark it clearly `# STUB — replaced in H5`.
- [ ] `types.ts` mirrors `contracts.py` exactly. `api.ts` has typed functions for every endpoint (same style as `frontend/src/services/api.ts`).
- [ ] `test_contract_fixtures.py`: every fixture validates against `IncidentStateDTO` / `IncidentSummary`.
- [ ] `start.sh`: creates the venv and installs if missing, runs uvicorn on 8000 and vite, and cleans up both on Ctrl-C.
- [ ] CI: Python 3.12 → `pip install -r backend/requirements.txt && cd backend && pytest -q`; Node 22 → `cd frontend && npm ci && npm run build && npm run lint`.
- [ ] PR template with the checklist from PLAN §6.

## Acceptance criteria
- `curl localhost:8000/incident/state` returns valid fixture JSON; the existing `/overview` and all other routes still work.
- `pytest -q` is green; `npm run build` is green with the new types compiled (import them somewhere trivial if tree-shaking complains).
- CI passes on the PR.

## Out of scope
Any real logic. No UI.
