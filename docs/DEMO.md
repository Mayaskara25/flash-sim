# Round 2 live demo run sheet

This is a **simulation** using synthetic positions and scripted scenario inputs. No trading, customer messaging, or fund movement occurs outside this local app. Use the live API (`/` with no `?mock=1`) at **8×**. The scenario clock is authoritative; the wall times below are approximate.

## Before the judges enter

1. Install backend requirements and frontend packages while online. Run `python -m pytest -q` from `backend/`, then `npm run build` and `npm run lint` from `frontend/`.
2. Start the API and Vite with `start.ps1` (Windows) or `./start.sh` (Linux/macOS). Check `http://127.0.0.1:8000/health`, then open `http://127.0.0.1:5173/` at 1280×720 or larger.
3. Select **All** roles, **C1 · Black Tuesday**, speed **8×**, and click **Reset** if an earlier run remains. Keep `?debug=1` available only as a recovery view.
4. Verify the header says **SIMULATION**, the state is idle, and the scenario picker lists C1–C6. Open **Assumptions** once and state that the thresholds, book, forecast paths, and controls are prototype assumptions.

## C1: controlled branch (about 7½–9 wall minutes)

| Sim clock / wall time | Operator clicks | Speaker cue / expected evidence |
|---|---|---|
| T+0 / 0:00 | Click **Start C1**. | IC: “We are replaying a synthetic leveraged book, not a live exchange.” |
| T+0:30 / 0:04 | In the log, acknowledge the LIQ_RATE alert. Approve the **Acknowledge active incident alert** action if it occupies the first IC slot. Then approve **Consider capping leverage on new positions** with a concrete rationale. | IC: WARNING arrives around T+0:28; LAR stays near 1, so the move is market explained. Leverage cap affects new positions, not the existing book. The decision appears in the log. |
| T+6:30 / 0:49 | Switch to **CS**; open **Volatility notice (T1)** and **Top-3 FAQ (T11)**, edit if needed, send both with a named actor. Return to **All**. | CS: ticket rate and I1 rise. Messages remain drafts until approved. |
| T+14–18 / 1:45–2:15 | Read the forecast strip and fund runway; in IC actions approve **Switch affected instruments to reduce-only** by T+18 with a rationale. Send the surfaced **Reduce-only notice (T3)**. Record **market-explained** in Abnormal liquidation review with the LAR evidence. | IC: CRITICAL and fund near 40%. Show the paired what-if badge before approval; the real control changes the subsequent path. TL: check that the liquidation engine is not over-firing. |
| T+35–40 / 4:23–5:00 | Watch signals settle; when the pending step-down appears, select **IC** and click **Confirm**. | IC: recovery needs five sim-minutes below band and a human confirmation. State becomes STABILISING. |
| T+55–58 / 6:53–7:15 | Confirm the pending resolution as **IC**. Open the generated summary; optionally send T12 resolution notice. | IC: RESOLVED. Show transitions, two control decisions, communications, peaks, liquidation verdict, and any open items. |

The calibrated C1 path starts at a mild drawdown, sustains WARNING through roughly T+11, reaches CRITICAL around T+11–14, then has a later second waterfall. Avoid quoting the older illustrative “6% at T+0” line from the source spec as a measured output.

## No-action comparison

After capturing the controlled summary, click **Reset**, start C1 again, and leave reduce-only unapproved. Use `?debug=1` only if time is short; **T+22** is a forward jump that preserves intermediate simulation ticks. The insurance fund crosses 25% around T+20–28 and the **Insurance fund below 25%** override forces EMERGENCY. Explain that the forecast and control what-if were shown before the threshold crossing. Do not describe this branch as the resolved operator run.

## C3 classifier branch (about 2–3 wall minutes)

Reset, select **C3 · Is it us or the market?**, and start at 8×. At T+3, show a mild price move with **LAR around 3.5**, classifier **SYSTEM**, tag **P1**, and the wrongful-liquidation override. Approve the proposed **Pause liquidations** control as IC, noting the 10-minute expiry and bad-debt tradeoff. Record a **wrongful** liquidation review with rationale. The summary then lists compensation review as an open item. T4 is a draft after the pause approval.

## Recovery during a live run

| Symptom | Action |
|---|---|
| Browser reload or lost tab | Reopen `http://127.0.0.1:5173/`. The backend session remains until reset. |
| API unavailable | Check `http://127.0.0.1:8000/health`; restart with `start.ps1` or `./start.sh`. Restarting the API resets the in-memory incident. |
| Behind the intended beat | Open `/?debug=1` and use a forward time jump. A jump processes all intervening ticks. Never jump past a planned decision before entering it. |
| Need a clean run | Click **Reset**, or POST `http://127.0.0.1:8000/incident/reset`; choose the scenario and start again. |
| Forecast panel missing | Check whether the run is live rather than `?mock=1`, and wait for the next ten simulated seconds. Forecasts intentionally hide when null. |
| Message or control dialog reports an error | Leave the dialog open, read the API detail, correct the actor/rationale/text and retry. |

## Brief checklist

- [x] Simulated feed with multiple signals and a book-driven liquidation rate.
- [x] Threshold alerts, severity escalation, and hard overrides.
- [x] Human-approved communication templates.
- [x] Append-only alert, transition, decision, and message log with liquidation review.
- [x] Three-role console, capped signals/actions, and analyst drill-downs.
- [x] Deterministic forecast, insurance-fund runway, and control what-ifs, labelled as simulated.
- [x] C1–C6 compound scenarios and temporary inject overlays.
- [ ] Two consecutive full 8× C1 browser rehearsals and one 8× C3 browser rehearsal recorded below.
- [ ] Actual demo laptop installation and projector test at 1280×720.

## Rehearsal record

Record the date, run, start/end wall time, observed transitions, operator actions, and fixes here after each **actual** rehearsal. Golden tests are automated validation; they do not count as an on-stage rehearsal.

| Date | Run | Wall duration | Result | Issues/fixes |
|---|---|---:|---|---|
| — | C1 rehearsal 1 | — | Pending | — |
| — | C1 rehearsal 2 | — | Pending | — |
| — | C3 rehearsal | — | Pending | — |
