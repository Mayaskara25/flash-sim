# H8: Scenario pack C2–C6, live injects, golden tests

| | |
|---|---|
| Branch | `h8-scenarios` |
| Owner | A or B |
| Size | M |
| Depends on | H5 (H1 `SCHEMA.md` is enough to start writing JSON) |
| Blocks | H10 |

## Goal
Add the other five compound scenarios from SPEC §8 so judges can see that the tool generalises. Each one should highlight a different decision (the "What it tests" column). Tune the live injects used in the demo's optional branch.

## Read first
SPEC §5–8 · H1 `scenarios/SCHEMA.md` · H2 classifier rules · H5 golden test as a template

## You own
`backend/incident/scenarios/C2_depeg_spiral.json`, `C3_is_it_us.json`, `C4_cant_get_out.json`, `C5_naked_book.json`, `C6_bad_actor.json`, the inject overlays table in `session.py` (small, coordinate with A), `backend/tests/test_scenarios_golden.py`

## Scenario targets (no-operator-action run unless stated)

| Chain | Must show | Key tracks/faults | Golden expectations |
|---|---|---|---|
| C2 Depeg spiral | Collateral verdict; wrong-way risk | STBL_PX 1.0 → 0.978 (T+2) → 0.965 (T+8, held 6 min); PX mild −3%; LIQ_RATE rises via LAR_MULT to mimic collateral haircut; RUMOR_MENTIONS up at T+12; WDR_QUEUE_RATIO → 95% at T+18 | verdict COLLATERAL by T+3; tags S1 → I2 → S4; EMERGENCY via the STBL override at ~T+13; T5, T7, T6 surfaced |
| C3 Is it us or the market? | Market-vs-system classifier | PX −2%; `LAR_MULT` 3.5 from T+1; ENGINE_ERR flag via API_ERR_PCT 1.5% | verdict SYSTEM; tag P1 (not M1); EMERGENCY via override; `pause_liqs` proposed first, with a 10-min expiry; T4 surfaced; IC can mark liquidations `wrongful` |
| C4 Can't get out | Fairness: pause liqs for affected users | M1 move −8%; ORDER_LATENCY 6000 ms + API_ERR 12% from T+4; `cannot_close` T+5–T+9; UPI_FAIL 30% from T+10 | P2 then R1 tags; override "cannot close 3+ min" at T+8; `load_shed` + `pause_liqs` proposed; T2, T6, T9 |
| C5 Naked book | Treasury view, not customer view | M1 −7%; LP_REJECT 25% from T+5; NET_EXPOSURE_PCT → 120% by T+12 | tag S3; CRITICAL (not EMERGENCY); T9 partner notice; fallback venue action for IC |
| C6 Bad actor | Security beats everything | M1 + I1; flag `wallet_compromise_suspected` at T+11; WDR_QUEUE surge | P3 action is priority #1 above all others; EMERGENCY immediately; `freeze_hot_wallet` proposed; T7 |

Injects (for the C1 demo's optional branch, SPEC §12.2): `stablecoin_dip` (STBL_PX → 0.982 for 3 min, then back), `oracle_stale` (ORACLE_AGE 20 s for 90 s), `api_overload` (latency 2000 ms for 2 min), `rumour` (RUMOR_MENTIONS 40/min for 4 min). Each should add its tag and surface its template without breaking C1's main arc.

## Acceptance criteria
- Each scenario's golden test is green and deterministic.
- `GET /incident/scenarios` lists C1–C6 with one-line descriptions a judge can understand.
- Each scenario runs to its peak within ~3 min wall time at 8×.
