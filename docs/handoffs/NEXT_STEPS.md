# Next Steps: where the build stands and how to carry on

_Written 2026-09-25. Read this first if you're picking the work up. The plan itself is `docs/PLAN.md`; this file only records the current state._

## 1. Status per handoff

| ID | Status | Where |
|---|---|---|
| H0 | ✅ done, merged | `main` |
| H3, H4, H6, H9 | ✅ done (pushed to `main` directly, verified: nothing lost, 48 tests + build/lint green) | `main` |
| H1 | 🟡 code done, **C1 calibration being re-tuned** (see §3) | local branch `h1-signals` |
| H2 | ✅ done + resolve-rule change (PLAN decision 13) + C1 integration test | local branch `h2-rules` (stacked on `h1-signals`) |
| H5 | ⏳ not started (branch/worktree created, empty) | `h5-session-api` (stacked on `h2-rules`) |
| H7, H8 | ⏳ not started, need H5 | — |
| H10 | ⏳ last | — |

## 2. Branch stack (merge in exactly this order)

```
main ─▶ h1-signals ─▶ h2-rules ─▶ h5-session-api ─▶ h7-forecast
                                                  └▶ h8-scenarios
```
- `h1-signals`, `h1-calibration-wip`, `h2-rules` and `h5-session-api` exist **only on the author's laptop** until pushed:
  `git push -u origin h1-signals h1-calibration-wip h2-rules h5-session-api`
- Open PRs in the same order (H1 → main, then H2, …). After each merge, rebase the next branch onto `main`.
- The branch `h1-fix-calibration` is already contained in `h1-signals` and can be deleted.
- **Only one agent/person per checkout.** Two agents writing to the same folder caused branch mix-ups twice. Use `git worktree add <path> <branch>` for parallel work.

## 3. The open issue: C1 calibration (H1)

The demo (SPEC §12.2) needs this shape for C1 with no operator action:

| Sim time | Target |
|---|---|
| T-2:00 → T+0 | NORMAL/WATCH (calm pre-roll) |
| T+0 → T+2 | LIQ_RATE crosses 100/min → **WARNING** |
| **T+1 → T+11** | **stays WARNING**: LIQ_RATE 100–290/min, nothing critical, S < 50 |
| T+12 → T+15 | LIQ_RATE 350–500 → **CRITICAL**, insurance fund 35–45% at T+14 |
| through T+18 | LIQ_RATE ≥ 150 (the cascade is still going) |
| T+20 → T+26 | fund < 25% → **EMERGENCY** (override) |
| reduce-only approved at T+18 | never EMERGENCY, fund ≥ 28%, LIQ < 50 by T+45, **RESOLVED by T+58** |
| always | classifier never says SYSTEM/PRICING/COLLATERAL in C1 |

**State before the round-2 fix:** everything hit except the WARNING phase. C1 went CRITICAL at T+1 (LIQ_RATE spiked to 1,677/min at T+3), and liquidations collapsed to ~20/min after T+14. The cause is that the initial drop crosses the dense high-leverage cluster almost at once.

**Round 2 is half done. It's on branch `h1-calibration-wip` (one commit on top of `h1-signals`):**
- ✅ `book.py`: a **liquidation-engine throughput queue**. Crossed positions queue up and execute at `book.liq_capacity_per_min` per minute. Shortfall is priced at execution time. `expected_liq_rate()` uses the same queue without `LAR_MULT`, so LAR ≈ 1 in C1. Unused capacity does not roll over (that was a bug that caused cliffs).
- ✅ `scenario_loader.py`: `BookSpec.liq_capacity_per_min` (default unbounded, so other scenarios behave as before). `signals.py` uses the new LAR denominator.
- ✅ Harness scripts: `backend/scripts/c1_calibration/calib.py` (tuning harness) and `integ.py` (runs C1 through the full rules pipeline and prints state transitions).
- ❌ **Not done:**
  - Write the final numbers into `scenarios/C1_black_tuesday.json` (PX track, `liq_capacity_per_min`, `slippage`, `expected` bands).
  - Update `SCHEMA.md`.
  - Rewrite `tests/test_book.py` (it calls a removed method and **fails as-is**).
  - Update `tests/test_signals_c1.py`: relax `PX_CHG_5M <= -5 at T+3` (now optional), widen the first-bad-debt window, and add assertions for LIQ 100–290 over T+2..T+11 and LIQ ≥ 150 through T+18.
  - Then rebase `h2-rules` and add the same WARNING-phase assertions to `test_c1_integration.py`.

**Findings so far (use them, don't rediscover them):**
- A 3-leg price track works: (1) gentle ramp T+0→T+11 to about −4.7%. This already passes the WARNING-phase target. (2) A sharp leg T+11→T+14 to about −9.7%, with capacity ~400/min giving LIQ 350–500 at T+14. (3) A second "waterfall" leg T+18→T+21 that takes the no-action fund below 25%; reduce-only at T+18 dampens it.
- With capacity 400 and slippage 0.25, the **reduce-only branch already passes** (fund floor 39%, resolves).
- **Remaining problem:** in the no-action run the fund must sit at 35–45% at T+14 and *not* collapse by T+15. Sustained ~400/min execution at a fixed deep price drains the fund each minute. Fix: a **fast partial bounce**, where price recovers about 55–70% of the T+11–14 leg *by T+15* (to roughly −6.3% depth), holds through T+18, then the waterfall leg. Search `(trough depth, bounce_frac, waterfall depth, capacity, slippage)` with the harness, checking both runs together.

**How to finish:** check out `h1-calibration-wip`, finish the ❌ items, run `pytest -q`, then squash/merge it into `h1-signals`. Then `git checkout h2-rules && git rebase h1-signals`, add the integration assertions, and run pytest.

**How to check it's finished:**
```bash
git log --oneline main..h2-rules                  # H1 commits (incl. the calibration), then 2 H2 commits
cd backend && .venv/bin/python -m pytest -q        # all green
.venv/bin/python scripts/c1_calibration/integ.py   # WARNING T+1..T+11, CRITICAL ~T+14, EMERGENCY T+20–26 (no action); RESOLVED by T+58 (reduce-only)
```

## 4. What to do next, in order

1. **Finish/verify H1 calibration** (§3). Commit on `h1-signals`, rebase `h2-rules` onto it, then run pytest.
2. **H5: session + real API.** Follow `docs/handoffs/H5-session-api.md`. Branch `h5-session-api` (rebase it onto `h2-rules` first). Things the handoff doesn't say:
   - The frontend (H4/H6/H9, already on `main`) was built against the H0 stub. Read `frontend/src/incident/api.ts` and `useIncident.ts` and make the real API satisfy both `docs/CONTRACTS.md` and what the UI actually calls. Note any mismatch.
   - Template ids are lowercase (`t1`…`t12`) everywhere; keep it that way.
   - The golden test must use a fake clock (no sleeping). Scripted operator run: leverage cap ~T+0:30 → T1 + T11 ~T+6:30 → reduce-only ~T+14:40 → T3 → IC confirms. Expect never EMERGENCY and RESOLVED by T+58. No-action variant: EMERGENCY T+20–28.
   - Leave `forecast: null` and a `session.forecaster` hook for H7.
   - Then check in the browser: `./start.sh`, open http://localhost:5173, start C1 at 8×, and click through to RESOLVED (this also completes H6's live acceptance).
3. **H7 (prediction) and H8 (scenarios C2–C6) in parallel**, each in its own worktree, both branched from `h5-session-api`. Follow their handoff files.
4. **H10** demo hardening together (`docs/handoffs/H10-demo-hardening.md`).

## 5. Verification checklist for every handoff (do this before merging)

- `cd backend && .venv/bin/python -m pytest -q` is green.
- `cd frontend && npm run build && npm run lint` is green (the 2 warnings in `SimContext.tsx` are pre-existing).
- `git diff --stat main...<branch>` only touches that handoff's "You own" files.
- Walk the handoff's acceptance criteria one by one. **Test the real pipeline, not just unit tests:** H1+H2 passed their own tests but failed together, and only `test_c1_integration.py` catches that.
- Backend contract (`contracts.py`), frontend types (`types.ts`) and `CONTRACTS.md` still agree.

## 6. Environment notes

- Linux: `./start.sh` starts both servers. Windows: `start.ps1`.
- If `npm run build` fails on Linux with a rolldown binding error, delete `frontend/node_modules` and run `npm install` (it was installed from Windows).
- Python venv: `backend/.venv` (`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
