# Interface Contracts

These are the only shapes that cross handoff boundaries. H0 turns this file into code in two places that must stay identical:

- `backend/incident/contracts.py` (pydantic v2 models, the source for validation)
- `frontend/src/incident/types.ts` (TS mirror)

Any change touches all three files in one PR, reviewed by both people (PLAN §6). All times are **sim-seconds** (`t`, int, 0 = scenario T+0, negative = pre-roll). Labels use `T+MM:SS` or `T-MM:SS`.

---

## 1. Enums

```ts
type Role = 'IC' | 'TL' | 'CS' | 'system'
type SignalStatus = 'normal' | 'watch' | 'warn' | 'critical'
type IncidentState = 'NORMAL' | 'WATCH' | 'WARNING' | 'CRITICAL' | 'EMERGENCY' | 'STABILISING' | 'RESOLVED'
type SevLevel = 1 | 2 | 3 | 4                // 1 = worst
type Tag = 'M1'|'M2'|'M3'|'M4'|'M5'|'M6'|'S1'|'S2'|'S3'|'S4'|'S5'|'P1'|'P2'|'P3'|'R1'|'R2'|'I1'|'I2'
type Verdict = 'MARKET' | 'SYSTEM' | 'PRICING' | 'COLLATERAL' | 'INFORMATION' | 'NONE'
type LogType = 'alert' | 'transition' | 'decision' | 'comm' | 'note'
type LiqReview = 'market-explained' | 'under-review' | 'wrongful'
type ActionStatus = 'proposed' | 'approved' | 'skipped' | 'done' | 'expired'
type TemplateStatus = 'surfaced' | 'sent' | 'dismissed'
```

State → SEV mapping (PLAN §3.7): EMERGENCY→1, CRITICAL→2, WARNING→3, everything else→4. STABILISING keeps the SEV of the state it came from until confirmed down.

## 2. Signal catalogue (backend constant, served at `GET /incident/catalogue`)

`direction: 'up'` means higher is worse; `'down'` means lower is worse. `watch` is our assumption (the "baseline band" edge); the other columns are SPEC §9.1.

| code | unit | baseline | watch | warn | critical | direction | tags |
|---|---|---|---|---|---|---|---|
| PX_CHG_5M | % | 0 | −2 | −5 | −10 | down | M1, M3 |
| LIQ_RATE | /min | 5 | 30 | 100 | 300 | up | M1, M2 |
| LAR | ratio | 1.0 | 1.5 | 2.0 | 3.0 | up | P1, M4 |
| INS_FUND_PCT | % | 100 | 90 | 60 | 25 | down | M2, M3 |
| BAD_DEBT_RATE | %fund/min | 0 | 0.01 | 0.01 | 2 | up | M2 |
| ADL_COUNT | count | 0 | — | — | 1 | up | M2 |
| NEG_BAL_ACCTS | count | 0 | — | 1 | 50 | up | M3 |
| ORACLE_DEV | % | 0.05 | 0.3 | 0.5 | 1.5 | up | M4 |
| ORACLE_AGE | s | 1 | 3 | 5 | 15 | up | M4 |
| STBL_PX | USD | 1.000 | 0.995 | 0.985 | 0.97 | down | S1 |
| SETTLE_FAIL_PCT | % | 0.2 | 1 | 2 | 10 | up | S2 |
| LP_REJECT_PCT | % | 0.5 | 2 | 5 | 20 | up | S3 |
| NET_EXPOSURE_PCT | % of limit | 20 | 50 | 70 | 100 | up | S3, M5 |
| WDR_QUEUE_RATIO | % | 5 | 25 | 50 | 90 | up | S4 |
| INR_BASIS_PCT | % | 0.2 | 0.5 | 1 | 3 | up | S5 |
| ORDER_LATENCY_P95 | ms | 80 | 400 | 1000 | 5000 | up | P2 |
| API_ERR_PCT | % | 0.3 | 1 | 2 | 10 | up | P2 |
| UPI_FAIL_PCT | % | 1 | 3 | 5 | 25 | up | R1 |
| TICKET_RATE | × baseline | 1 | 2 | 3 | 8 | up | I1 |
| SENTIMENT | −1…+1 | 0.1 | −0.2 | −0.4 | −0.7 | down | I1, I2 |
| RUMOR_MENTIONS | /min | 0 | 5 | 20 | 60 | up | I2 |

Notes: `NET_EXPOSURE_USD` from the spec is expressed as `NET_EXPOSURE_PCT` of the risk limit. `RUMOR_MENTIONS` is added for I2. `PX` (the underlying price level, USD) is also emitted but has no thresholds; it is for the price chart.

```ts
type SignalDef = { code: string; label: string; unit: string; baseline: number; watch: number|null;
  warn: number|null; critical: number|null; direction: 'up'|'down'; tags: Tag[] }
```

## 3. SignalFrame (H1 → H2/H5/H7, backend-internal)

```python
@dataclass(frozen=True)
class SignalFrame:
    t: int                            # sim seconds
    values: dict[str, float]          # every catalogue code + "PX"
    flags: dict[str, bool]            # see below
    meta: dict[str, float]            # debug: L_obs, L_exp, n_open, fund_usd, ...
```

Flags (booleans that feed hard overrides / dimensions): `cannot_close`, `wallet_compromise_suspected`, `regulatory_notice`, `partner_notice`, `media_attention`, `stablecoin_frozen_address`.

The rules engine (H2) keeps its own rolling history for duration rules ("STBL_PX < 0.97 for 5 min", "cannot_close for 3 min"); frames themselves are memoryless.

## 4. Controls and effects (H3 defines, H1 applies, H7 simulates)

```python
@dataclass(frozen=True)
class Effect:
    signal: str            # catalogue code or sim knob, e.g. "LIQ_RATE", "BAD_DEBT_RATE", "sim.new_exposure"
    op: Literal["mult", "add", "cap", "set"]
    value: float
    ramp_s: int = 60       # sim-seconds to reach full effect after approval

@dataclass(frozen=True)
class ControlDef:
    id: str                # "reduce_only", "leverage_cap", "raise_mm", "pause_liqs", "fallback_feed",
                           # "collateral_haircut", "pause_deposits", "ins_fund_topup", "load_shed", "freeze_hot_wallet"
    label: str
    reduces: str; tradeoff: str        # SPEC §9.4 text
    tags: list[str]
    time_box_s: int | None             # e.g. pause_liqs = 600
    effects: list[Effect]
    params: dict[str, float]           # e.g. {"max_leverage": 3}, {"topup_pct": 20}
```

Effects apply to *generated* values after the script, in the order approved. A `cap` never raises a value. When a time-boxed control expires, its effects stop and a "review" action is proposed.

## 5. IncidentStateDTO: `GET /api/incident/state`

```ts
type IncidentStateDTO = {
  sim: { scenario_id: string|null; scenario_name: string|null; t: number; t_label: string;
         speed: number; running: boolean; duration_s: number; started: boolean }
  severity: {
    state: IncidentState; sev: SevLevel; score: number            // S, 0–100
    dims: { F: number; B: number; A: number; V: number; R: number } // each 0–5
    overrides: string[]                                           // human text of active hard overrides
    since_t: number                                               // when current state entered
    pending: null | { kind: 'stepdown'|'resolve'; from: IncidentState; to: IncidentState;
                      eligible_since_t: number; needs: 'IC' }     // needs IC confirmation
  }
  classifier: { verdict: Verdict; lar: number; l_obs: number; l_exp: number; explanation: string }
  tags: { tag: Tag; name: string; active: boolean; first_t: number; peak_sev: SevLevel }[]
  signals: SignalView[]            // ALL signals, sorted: relevant first; UI expands at most 6
  alerts: AlertCard[]              // collapsed repeated alerts
  actions: ActionView[]            // all non-terminal + last 10 terminal; UI shows ≤ 3 proposed per role
  templates: TemplateView[]        // surfaced + recently sent
  controls_active: ActiveControl[]
  log: LogEntry[]                  // full log, oldest first (small enough for the demo)
  forecast: Forecast | null        // H7; null until implemented / before T+0
  reminders: string[]              // e.g. "Customer update overdue (last T+14:40)"
}

type SignalView = { code: string; label: string; unit: string; value: number; status: SignalStatus;
  relevant: boolean;               // tied to an active tag or status >= watch
  trend_per_min: number; history: [number, number][];   // last 10 sim-min, [t, v]
  thresholds: { watch: number|null; warn: number|null; critical: number|null }; direction: 'up'|'down' }

type AlertCard = { id: string; signal: string; level: 'warn'|'critical'; count: number;
  first_t: number; last_t: number; acknowledged_by: Role|null }

type ActionView = { id: string; tag: Tag|null; role: Role; text: string; priority: number; // lower = sooner
  control_id: string|null; template_id: string|null; status: ActionStatus;
  proposed_t: number; decided_t: number|null; decided_by: Role|null; rationale: string|null;
  rationale_hint: string;          // pre-filled suggestion using live numbers
  expires_t: number|null; what_if: WhatIf|null }        // what_if filled by H7

type TemplateView = { id: string; tag: Tag|null; audience: string; channel: string; title: string;
  text: string;                    // pre-filled with live values
  missing: string[];               // placeholders we could not fill
  status: TemplateStatus; surfaced_t: number; sent_t: number|null; approved_by: Role|null }

type ActiveControl = { control_id: string; label: string; approved_t: number; approved_by: Role;
  expires_t: number|null; params: Record<string, number> }

type LogEntry = { id: number; t: number; t_label: string; type: LogType; sev: SevLevel;
  scenario_tags: Tag[]; actor: Role; action: string; rationale: string|null;
  signal_snapshot: Record<string, number>; liquidation_review: LiqReview|null;
  approved_by: Role|null; expires_at: number|null; ref: string|null }  // ref = action/template/control id
```

## 6. Forecast (H7)

```ts
type Forecast = {
  computed_t: number; horizon_min: [5, 10, 15]; n_paths: number
  sev_probs: { h: number; p: Record<'1'|'2'|'3'|'4', number> }[]      // per horizon
  eta_sev1_min: { p50: number|null; p90: number|null; prob_within_15: number }
  ins_fund: { h: number; p10: number; p50: number; p90: number }[]    // INS_FUND_PCT
  eta_fund_25_min: { p50: number|null; p90: number|null; prob_within_15: number }
  drivers: { signal: string; contribution: number; text: string }[]   // top 3
  cascade_model_p: number          // existing sklearn cascade probability, reused as a driver
  headline: string                 // "SEV-1 likely in ~6 min (p 0.68)"
  label: 'Simulated projection — not a market forecast'
}
type WhatIf = { control_id: string; p_sev1_15_before: number; p_sev1_15_after: number;
  fund_p50_15_before: number; fund_p50_15_after: number; text: string }
```

## 7. Endpoints (all under `/api` through the Vite proxy; backend paths have no `/api`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/incident/scenarios` | — | `{id,name,description,duration_s,tags_expected}[]` |
| GET | `/incident/catalogue` | — | `{signals: SignalDef[], controls: ControlDef[], templates: {id,audience,channel,title,trigger}[]}` |
| POST | `/incident/start` | `{scenario_id, speed?=8}` | state |
| POST | `/incident/clock` | `{op: 'pause'|'resume'|'speed'|'jump', speed?, t?}` | state (`jump` = debug seek forward) |
| POST | `/incident/reset` | — | state (no scenario) |
| GET | `/incident/state` | — | state |
| POST | `/incident/alerts/{id}/ack` | `{actor}` | state |
| POST | `/incident/actions/{id}/decide` | `{decision:'approve'|'skip'|'done', actor, rationale}` | state (rationale required for approve/skip) |
| POST | `/incident/templates/{id}/send` | `{actor, text}` | state (text may be edited) |
| POST | `/incident/templates/{id}/dismiss` | `{actor, rationale}` | state |
| POST | `/incident/notes` | `{actor, text}` | state |
| POST | `/incident/severity` | `{sev, actor, reason}` | state (manual raise any time; lower only via pending) |
| POST | `/incident/pending/confirm` | `{actor:'IC'}` | state |
| POST | `/incident/liquidations/review` | `{verdict: LiqReview, actor, rationale}` | state |
| POST | `/incident/inject` | `{event: 'stablecoin_dip'|'oracle_stale'|'api_overload'|'rumour'}` | state |
| GET | `/incident/summary` | — | `IncidentSummary` |

Errors: `409` for an invalid transition (e.g. deciding an already-decided action), `422` for missing rationale. Body: `{detail: string}`.

```ts
type IncidentSummary = { scenario_id: string; started_t: number; ended_t: number|null; peak_sev: SevLevel;
  timeline: LogEntry[];            // transitions only
  peaks: { signal: string; value: number; t: number }[]
  decisions: LogEntry[]; comms: LogEntry[]
  liquidation_reviews: LogEntry[]; open_items: string[]; markdown: string }
```

## 8. Fixtures

`docs/contracts/fixtures/state_{idle,normal,warning,critical,emergency,stabilising,resolved}.json` and `summary_c1.json`. They are hand-written in H0 and validated against the pydantic models by `backend/tests/test_contract_fixtures.py`. The frontend's mock mode (`VITE_INCIDENT_MOCK=1`) cycles through them. When the contract changes, update the fixtures in the same PR.
