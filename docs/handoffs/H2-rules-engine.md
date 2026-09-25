# H2: Rules engine (severity, overrides, classifier, state machine, tags, alerts)

| | |
|---|---|
| Branch | `h2-rules` |
| Owner | A (or a third person/agent, since it is pure and fenced) |
| Size | M |
| Depends on | H0 |
| Blocks | H5, H7 |

## Goal
Pure, deterministic functions from a stream of `SignalFrame`s to severity, state, verdict, tags and alert cards, exactly per SPEC §3, §9.2 and §9.3. No I/O, no HTTP. Tests can feed hand-built frames.

## Read first
SPEC §3, §4 (tags and names), §8 (priority rule), §9.1–9.3 · CONTRACTS §1–3, §5 (`severity`, `classifier`, `tags`, `alerts`)

## You own
`backend/incident/rules/__init__.py`, `rules/history.py`, `rules/severity.py`, `rules/classifier.py`, `rules/state_machine.py`, `rules/tags.py`, `rules/alerts.py`, `backend/tests/test_severity.py`, `test_classifier.py`, `test_state_machine.py`, `test_tags_alerts.py`

## Design

**`history.py`:** `SignalHistory` (ring buffer, 15 sim-min) with `value_at(code, t)`, `held(pred, code, seconds)` for duration rules, and `stress(code)`, where stress ∈ [0, 1] is the position between baseline and critical.

**`severity.py`:** `score(frame, history, overrides_state) -> SeverityResult(score, dims, overrides)`

Dimension rules (each 0–5; take the max of contributing rules). Signal status comes from `catalogue.status_of`: watch = 1, warn = 3, critical = 5 unless stated otherwise.
- **F, customer funds:** LAR status *only if the classifier verdict ≠ MARKET*; ORACLE_DEV; STBL_PX; WDR_QUEUE_RATIO (warn 2, crit 4); NEG_BAL_ACCTS (warn 2, crit 4); `wallet_compromise_suspected` → 5.
- **B, balance sheet:** `5 × clip((100 − INS_FUND_PCT) / 50, 0, 1)`; BAD_DEBT_RATE > 0 → ≥ 2; NET_EXPOSURE_PCT status.
- **A, availability:** ORDER_LATENCY_P95, API_ERR_PCT, UPI_FAIL_PCT, SETTLE_FAIL_PCT, LP_REJECT_PCT (warn 2, crit 4); `cannot_close` → 5.
- **V, velocity:** take the worst-stress signal. If its stress ≥ 0.2, `ratio = stress_now / max(stress_5min_ago, 0.05)` and `V = clip((ratio − 1) × 5, 0, 5)` (doubling in 5 min → 5).
- **R, reputation/regulatory:** TICKET_RATE (warn 1, crit 3), SENTIMENT (warn 2, crit 4), RUMOR_MENTIONS (warn 2, crit 4), `media_attention` → 3, `partner_notice` → 3, `regulatory_notice` → 5.
- `S = 20 × (0.30F + 0.25B + 0.15A + 0.15V + 0.15R)`, rounded to 1 dp.

Hard overrides (SPEC §3). Each returns human text:
1. Classifier verdict SYSTEM or PRICING with LAR critical.
2. INS_FUND_PCT < 25, or ADL_COUNT > 0.
3. STBL_PX < 0.97 held for 300 s.
4. `cannot_close` held for 180 s.
5. `wallet_compromise_suspected`.

**`classifier.py`:** `classify(frame, history) -> ClassifierResult(verdict, lar, l_obs, l_exp, explanation)`, per SPEC §9.2 in this precedence: COLLATERAL (LAR high and STBL_PX < 0.985) → PRICING (LAR high and ORACLE_DEV ≥ warn) → SYSTEM (LAR > 2.0 and |PX_CHG_5M| < 3) → MARKET (LAR 0.7–1.5 and PX_CHG_5M ≤ −2, or LIQ_RATE ≥ watch) → INFORMATION (TICKET_RATE or SENTIMENT ≥ warn and nothing else ≥ warn) → NONE. The explanation is one plain sentence with numbers.

**`state_machine.py`:** `StateMachine.step(t, sev_result, frame, history) -> (state, transitions[])`
- Target from thresholds: any status ≥ watch → WATCH; ≥ warn or S ≥ 30 → WARNING; ≥ critical or S ≥ 50 → CRITICAL; S ≥ 70 or any override → EMERGENCY.
- Up: immediate, emitting a `transition` event.
- Down from EMERGENCY or CRITICAL: when the target has been lower for 300 s continuously, set `pending = stepdown` (to STABILISING); it needs `confirm(actor='IC')`.
- STABILISING → CRITICAL if any signal re-crosses critical. STABILISING → pending `resolve` when all signals are < warn for 900 s; IC confirms → RESOLVED.
- From WARNING/WATCH, stepping down happens automatically after 300 s (spec only requires IC confirmation from Critical/Emergency).
- `manual_raise(sev, actor, reason)` is always allowed.
- SEV derivation per CONTRACTS §1.

**`tags.py`:** a signal at ≥ warn activates its catalogue tags, *except* that the liquidation signals (LIQ_RATE, LAR) use the classifier verdict: MARKET → M1 (+ M2 if INS_FUND ≤ warn or BAD_DEBT > 0), SYSTEM → P1, PRICING → M4, COLLATERAL → S1. Tags stay in the list forever; `active` = a trigger is present now. Track `first_t` and `peak_sev`. Provide `priority_order(tags)` per SPEC §8 (P3 → P1/M4/S1 → M2/M3/S3/S4 → P2/R1 → I1/I2 → rest).

**`alerts.py`:** one `AlertCard` per (signal, level). Repeated crossings increment `count` and update `last_t`. An escalation from warn to critical creates a new card and marks the warn card superseded.

## Acceptance criteria
- A table-driven test for every row of CONTRACTS §2 (below/at/above each threshold).
- Tests for each of the 5 overrides, including "held for N seconds" edges (N−2 s → no, N s → yes).
- Hysteresis: a signal oscillating around the critical threshold with a 60 s period never produces more than one downward transition in 10 min.
- Classifier: the 6 rows of SPEC §9.2 each have a test.
- Replaying C1 frames (a fixture file of frames is fine if H1 hasn't merged yet) gives WARNING near T+0 and CRITICAL near T+14.

## Out of scope
Actions, templates, log, HTTP.
