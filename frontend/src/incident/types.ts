// TypeScript mirror of backend/incident/contracts.py (docs/CONTRACTS.md is
// the source of truth; the two must stay identical field-for-field, see
// PLAN.md §6). Section numbers below refer to CONTRACTS.md.
//
// `SignalFrame` (CONTRACTS §3) is explicitly backend-internal (H1 ->
// H2/H5/H7) and never crosses HTTP, so it is intentionally not mirrored
// here.
//
// Two deliberate, documented deviations from the literal CONTRACTS.md
// snippets (both loosened on the Python side too, in contracts.py, so the
// two files still match each other exactly):
//   - `Forecast.horizon_min` is `number[]` here (not the literal tuple
//     `[5, 10, 15]`) — pydantic's runtime validation doesn't gain anything
//     from a fixed-literal tuple, and a plain array is what actually
//     crosses JSON.
//   - `SevProbPoint.p` is typed as the stricter `Record<'1'|'2'|'3'|'4',
//     number>` per CONTRACTS, while the Python side uses `dict[str,
//     float]` for simplicity; both are satisfied by the same fixture data.

export type Role = 'IC' | 'TL' | 'CS' | 'system'
export type SignalStatus = 'normal' | 'watch' | 'warn' | 'critical'
export type IncidentState =
  | 'NORMAL'
  | 'WATCH'
  | 'WARNING'
  | 'CRITICAL'
  | 'EMERGENCY'
  | 'STABILISING'
  | 'RESOLVED'
export type SevLevel = 1 | 2 | 3 | 4
export type Tag =
  | 'M1' | 'M2' | 'M3' | 'M4' | 'M5' | 'M6'
  | 'S1' | 'S2' | 'S3' | 'S4' | 'S5'
  | 'P1' | 'P2' | 'P3'
  | 'R1' | 'R2'
  | 'I1' | 'I2'
export type Verdict = 'MARKET' | 'SYSTEM' | 'PRICING' | 'COLLATERAL' | 'INFORMATION' | 'NONE'
export type LogType = 'alert' | 'transition' | 'decision' | 'comm' | 'note'
export type LiqReview = 'market-explained' | 'under-review' | 'wrongful'
export type ActionStatus = 'proposed' | 'approved' | 'skipped' | 'done' | 'expired'
export type TemplateStatus = 'surfaced' | 'sent' | 'dismissed'
export type Direction = 'up' | 'down'

// 2. Signal catalogue entry (GET /incident/catalogue -> CatalogueDTO.signals)
export type SignalDef = {
  code: string
  label: string
  unit: string
  baseline: number
  watch: number | null
  warn: number | null
  critical: number | null
  direction: Direction
  tags: Tag[]
}

// 4. Controls and effects (H3 defines; served read-only via /incident/catalogue)
export type Effect = { signal: string; op: 'mult' | 'add' | 'cap' | 'set'; value: number; ramp_s: number }
export type ControlDef = {
  id: string
  label: string
  reduces: string
  tradeoff: string
  tags: string[]
  time_box_s: number | null
  effects: Effect[]
  params: Record<string, number>
}

// 5. IncidentStateDTO: GET /incident/state
export type SimBlock = {
  scenario_id: string | null
  scenario_name: string | null
  t: number
  t_label: string
  speed: number
  running: boolean
  duration_s: number
  started: boolean
}

export type Dims = { F: number; B: number; A: number; V: number; R: number }

export type PendingTransition = {
  kind: 'stepdown' | 'resolve'
  from: IncidentState
  to: IncidentState
  eligible_since_t: number
  needs: 'IC'
}

export type SeverityBlock = {
  state: IncidentState
  sev: SevLevel
  score: number
  dims: Dims
  overrides: string[]
  since_t: number
  pending: PendingTransition | null
}

export type ClassifierBlock = { verdict: Verdict; lar: number; l_obs: number; l_exp: number; explanation: string }

export type TagView = { tag: Tag; name: string; active: boolean; first_t: number; peak_sev: SevLevel }

export type Thresholds = { watch: number | null; warn: number | null; critical: number | null }

export type SignalView = {
  code: string
  label: string
  unit: string
  value: number
  status: SignalStatus
  relevant: boolean
  trend_per_min: number
  history: [number, number][]
  thresholds: Thresholds
  direction: Direction
}

export type AlertCard = {
  id: string
  signal: string
  level: 'warn' | 'critical'
  count: number
  first_t: number
  last_t: number
  acknowledged_by: Role | null
}

export type WhatIf = {
  control_id: string
  p_sev1_15_before: number
  p_sev1_15_after: number
  fund_p50_15_before: number
  fund_p50_15_after: number
  text: string
}

export type ActionView = {
  id: string
  tag: Tag | null
  role: Role
  text: string
  priority: number
  control_id: string | null
  template_id: string | null
  status: ActionStatus
  proposed_t: number
  decided_t: number | null
  decided_by: Role | null
  rationale: string | null
  rationale_hint: string
  expires_t: number | null
  what_if: WhatIf | null
}

export type TemplateView = {
  id: string
  tag: Tag | null
  audience: string
  channel: string
  title: string
  text: string
  missing: string[]
  status: TemplateStatus
  surfaced_t: number
  sent_t: number | null
  approved_by: Role | null
}

export type ActiveControl = {
  control_id: string
  label: string
  approved_t: number
  approved_by: Role
  expires_t: number | null
  params: Record<string, number>
}

export type LogEntry = {
  id: number
  t: number
  t_label: string
  type: LogType
  sev: SevLevel
  scenario_tags: Tag[]
  actor: Role
  action: string
  rationale: string | null
  signal_snapshot: Record<string, number>
  liquidation_review: LiqReview | null
  approved_by: Role | null
  expires_at: number | null
  ref: string | null
}

// 6. Forecast (H7)
export type SevProbPoint = { h: number; p: Record<'1' | '2' | '3' | '4', number> }
export type InsFundPoint = { h: number; p10: number; p50: number; p90: number }
export type EtaEstimate = { p50: number | null; p90: number | null; prob_within_15: number }
export type Driver = { signal: string; contribution: number; text: string }

export type Forecast = {
  computed_t: number
  horizon_min: number[] // [5, 10, 15]; see file header note
  n_paths: number
  sev_probs: SevProbPoint[]
  eta_sev1_min: EtaEstimate
  ins_fund: InsFundPoint[]
  eta_fund_25_min: EtaEstimate
  drivers: Driver[]
  cascade_model_p: number
  headline: string
  label: 'Simulated projection — not a market forecast'
}

export type IncidentStateDTO = {
  sim: SimBlock
  severity: SeverityBlock
  classifier: ClassifierBlock
  tags: TagView[]
  signals: SignalView[] // ALL signals, sorted: relevant first
  alerts: AlertCard[]
  actions: ActionView[]
  templates: TemplateView[]
  controls_active: ActiveControl[]
  log: LogEntry[]
  forecast: Forecast | null
  reminders: string[]
}

// 7. Endpoints: request bodies + misc response shapes
export type ScenarioSummary = { id: string; name: string; description: string; duration_s: number; tags_expected: Tag[] }
export type TemplateCatalogueEntry = { id: string; audience: string; channel: string; title: string; trigger: string }
export type CatalogueDTO = { signals: SignalDef[]; controls: ControlDef[]; templates: TemplateCatalogueEntry[] }

export type StartBody = { scenario_id: string; speed?: number }
export type ClockBody = { op: 'pause' | 'resume' | 'speed' | 'jump'; speed?: number; t?: number }
export type AlertAckBody = { actor: Role }
export type ActionDecideBody = { decision: 'approve' | 'skip' | 'done'; actor: Role; rationale?: string | null }
export type TemplateSendBody = { actor: Role; text: string }
export type TemplateDismissBody = { actor: Role; rationale: string }
export type NotesBody = { actor: Role; text: string }
export type SeverityBody = { sev: SevLevel; actor: Role; reason: string }
export type PendingConfirmBody = { actor: 'IC' }
export type LiquidationReviewBody = { verdict: LiqReview; actor: Role; rationale: string }
export type InjectBody = { event: 'stablecoin_dip' | 'oracle_stale' | 'api_overload' | 'rumour' }

export type ErrorDetail = { detail: string }

export type PeakEntry = { signal: string; value: number; t: number }

export type IncidentSummary = {
  scenario_id: string
  started_t: number
  ended_t: number | null
  peak_sev: SevLevel
  timeline: LogEntry[] // transitions only
  peaks: PeakEntry[]
  decisions: LogEntry[]
  comms: LogEntry[]
  liquidation_reviews: LogEntry[]
  open_items: string[]
  markdown: string
}
