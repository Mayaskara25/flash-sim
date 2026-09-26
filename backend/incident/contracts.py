"""Pydantic v2 models (+ frozen dataclasses) for the incident console.

This file is the Python half of the interface contract in
`docs/CONTRACTS.md`. `frontend/src/incident/types.ts` is the TypeScript
mirror; the two must stay identical field-for-field (PLAN.md §6). Section
numbers in comments refer to CONTRACTS.md.

`SignalFrame`, `Effect` and `ControlDef` are plain frozen dataclasses per
the H0 handoff (CONTRACTS §3-4) — they are backend-internal / H1-H3 shapes,
not request/response bodies validated at the API boundary. Pydantic v2
supports stdlib dataclasses as BaseModel fields natively (validated and
serialized like any other field), so `ControlDef` still round-trips cleanly
through `GET /incident/catalogue` without being rewritten as a BaseModel.

Everything else here is a BaseModel because it crosses HTTP (request
bodies, `IncidentStateDTO`, `IncidentSummary`, the catalogue response).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# 1. Enums (CONTRACTS §1)
# ---------------------------------------------------------------------------

Role = Literal["IC", "TL", "CS", "system"]
SignalStatus = Literal["normal", "watch", "warn", "critical"]
IncidentState = Literal[
    "NORMAL", "WATCH", "WARNING", "CRITICAL", "EMERGENCY", "STABILISING", "RESOLVED"
]
SevLevel = Literal[1, 2, 3, 4]
Tag = Literal[
    "M1", "M2", "M3", "M4", "M5", "M6",
    "S1", "S2", "S3", "S4", "S5",
    "P1", "P2", "P3",
    "R1", "R2",
    "I1", "I2",
]
Verdict = Literal["MARKET", "SYSTEM", "PRICING", "COLLATERAL", "INFORMATION", "NONE"]
LogType = Literal["alert", "transition", "decision", "comm", "note"]
LiqReview = Literal["market-explained", "under-review", "wrongful"]
ActionStatus = Literal["proposed", "approved", "skipped", "done", "expired"]
TemplateStatus = Literal["surfaced", "sent", "dismissed"]
Direction = Literal["up", "down"]


# ---------------------------------------------------------------------------
# 2. Signal catalogue entry (CONTRACTS §2). Backend constant table lives in
#    catalogue.py as `SIGNALS: list[SignalDef]`; this is just the shape.
# ---------------------------------------------------------------------------


class SignalDef(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    label: str
    unit: str
    baseline: float
    watch: float | None
    warn: float | None
    critical: float | None
    direction: Direction
    tags: list[Tag]


# ---------------------------------------------------------------------------
# 3. SignalFrame (CONTRACTS §3, H1 -> H2/H5/H7, backend-internal)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalFrame:
    t: int  # sim seconds
    values: dict[str, float]  # every catalogue code + "PX"
    flags: dict[str, bool]  # cannot_close, wallet_compromise_suspected, ...
    meta: dict[str, float]  # debug: L_obs, L_exp, n_open, fund_usd, ...


# ---------------------------------------------------------------------------
# 4. Controls and effects (CONTRACTS §4, H3 defines, H1 applies, H7 sims)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Effect:
    signal: str  # catalogue code or sim knob, e.g. "LIQ_RATE", "sim.new_exposure"
    op: Literal["mult", "add", "cap", "set"]
    value: float
    ramp_s: int = 60  # sim-seconds to reach full effect after approval


@dataclass(frozen=True)
class ControlDef:
    id: str
    label: str
    reduces: str
    tradeoff: str
    tags: list[str]
    time_box_s: int | None
    effects: list[Effect]
    params: dict[str, float]


# ---------------------------------------------------------------------------
# 5. IncidentStateDTO: GET /incident/state (CONTRACTS §5)
# ---------------------------------------------------------------------------


class SimBlock(BaseModel):
    scenario_id: str | None
    scenario_name: str | None
    t: int
    t_label: str
    speed: float
    running: bool
    duration_s: int
    started: bool


class Dims(BaseModel):
    F: float
    B: float
    A: float
    V: float
    R: float


class PendingTransition(BaseModel):
    """Downward-transition request awaiting IC confirmation (hysteresis)."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["stepdown", "resolve"]
    from_: IncidentState = Field(alias="from")
    to: IncidentState
    eligible_since_t: int
    needs: Literal["IC"]


class SeverityBlock(BaseModel):
    state: IncidentState
    sev: SevLevel
    score: float
    dims: Dims
    overrides: list[str]
    since_t: int
    pending: PendingTransition | None


class ClassifierBlock(BaseModel):
    verdict: Verdict
    lar: float
    l_obs: float
    l_exp: float
    explanation: str


class TagView(BaseModel):
    tag: Tag
    name: str
    active: bool
    first_t: int
    peak_sev: SevLevel


class Thresholds(BaseModel):
    watch: float | None
    warn: float | None
    critical: float | None


class SignalView(BaseModel):
    code: str
    label: str
    unit: str
    value: float
    status: SignalStatus
    relevant: bool  # tied to an active tag or status >= watch
    trend_per_min: float
    history: list[tuple[int, float]]  # last 10 sim-min, [t, v]
    thresholds: Thresholds
    direction: Direction


class AlertCard(BaseModel):
    id: str
    signal: str
    level: Literal["warn", "critical"]
    count: int
    first_t: int
    last_t: int
    acknowledged_by: Role | None


class WhatIf(BaseModel):
    """Filled by H7; CONTRACTS §6 but embedded in ActionView (§5)."""

    control_id: str
    p_sev1_15_before: float
    p_sev1_15_after: float
    fund_p50_15_before: float
    fund_p50_15_after: float
    text: str


class ActionView(BaseModel):
    id: str
    tag: Tag | None
    role: Role
    text: str
    priority: int  # lower = sooner
    control_id: str | None
    template_id: str | None
    status: ActionStatus
    proposed_t: int
    decided_t: int | None
    decided_by: Role | None
    rationale: str | None
    rationale_hint: str  # pre-filled suggestion using live numbers
    expires_t: int | None
    what_if: WhatIf | None


class TemplateView(BaseModel):
    id: str
    tag: Tag | None
    audience: str
    channel: str
    title: str
    text: str  # pre-filled with live values
    missing: list[str]  # placeholders we could not fill
    status: TemplateStatus
    surfaced_t: int
    sent_t: int | None
    approved_by: Role | None


class ActiveControl(BaseModel):
    control_id: str
    label: str
    approved_t: int
    approved_by: Role
    expires_t: int | None
    params: dict[str, float]


class LogEntry(BaseModel):
    id: int
    t: int
    t_label: str
    type: LogType
    sev: SevLevel
    scenario_tags: list[Tag]
    actor: Role
    action: str
    rationale: str | None
    signal_snapshot: dict[str, float]
    liquidation_review: LiqReview | None
    approved_by: Role | None
    expires_at: int | None
    ref: str | None  # action/template/control id


# ---------------------------------------------------------------------------
# 6. Forecast (CONTRACTS §6, H7)
# ---------------------------------------------------------------------------


class SevProbPoint(BaseModel):
    h: int
    p: dict[str, float]  # keys '1'..'4' (SevLevel as string, JSON object keys)


class InsFundPoint(BaseModel):
    h: int
    p10: float
    p50: float
    p90: float


class EtaEstimate(BaseModel):
    p50: float | None
    p90: float | None
    prob_within_15: float


class Driver(BaseModel):
    signal: str
    contribution: float
    text: str


class Forecast(BaseModel):
    computed_t: int
    horizon_min: list[int]  # [5, 10, 15]
    n_paths: int
    sev_probs: list[SevProbPoint]  # per horizon
    eta_sev1_min: EtaEstimate
    ins_fund: list[InsFundPoint]  # INS_FUND_PCT
    eta_fund_25_min: EtaEstimate
    drivers: list[Driver]  # top 3
    cascade_model_p: float
    headline: str
    label: Literal["Simulated projection — not a market forecast"] = (
        "Simulated projection — not a market forecast"
    )


class ExecutionView(BaseModel):
    id: str
    cluster_id: str
    trader_id: str
    asset: str
    side: Literal["LONG", "SHORT"]
    leverage: float
    modelled_threshold: float
    observed_execution: float
    deviation_pct: float
    execution_delay_ms: float
    market_price: float
    liquidity_condition: str
    reasons: list[str]
    status: Literal["flagged", "valid", "investigate", "escalated"]
    label: str


class InvestigationCluster(BaseModel):
    id: str
    asset: str
    flagged_count: int
    executions: list[ExecutionView]
    why: str


class ActionQueueItem(BaseModel):
    id: str
    band: Literal["NOW", "NEXT", "MONITOR"]
    owner: str
    role: Role
    text: str
    reason: str
    status: str
    eta: str | None
    button: Literal["OPEN", "RUN", "APPROVE"] | None
    ref: str | None
    priority: int


class TeamMember(BaseModel):
    id: str
    role: Role
    title: str
    status: str
    responsibility: str


class WhyAlert(BaseModel):
    signal: str
    value: float
    baseline: float
    watch: float | None
    warn: float | None
    critical: float | None
    unit: str
    change_pct: float | None
    conclusion: str


class CommandDelta(BaseModel):
    elapsed_s: int
    since_label: str
    lines: list[str]


class CommandBrief(BaseModel):
    risk_level: Literal["NORMAL", "WATCH", "ACTION", "CRITICAL"]
    cascade_score: float
    incident_mode: bool
    reasons: list[str]
    first_priority: str
    why_first: str
    next_step: str
    liquidation_rate: float
    liquidation_baseline: float
    near_liquidation: int
    liquidity_change: float
    abnormal_liquidations: int
    lar: float
    exposure_pct: float
    px_chg: float
    ticket_rate: float
    largest_cluster: str | None
    cluster: InvestigationCluster | None
    queue: list[ActionQueueItem]
    team: list[TeamMember]
    delta: CommandDelta | None
    why_alerts: list[WhyAlert]
    label: str = "Simulated research prototype — modelled figures only."


class CopilotReply(BaseModel):
    answer: str
    spoken: str
    first_priority: str
    why: list[str]
    next_step: str
    facts: dict[str, float | int | str | None]


class IncidentStateDTO(BaseModel):
    sim: SimBlock
    severity: SeverityBlock
    classifier: ClassifierBlock
    tags: list[TagView]
    signals: list[SignalView]  # ALL signals, sorted: relevant first
    alerts: list[AlertCard]
    actions: list[ActionView]
    templates: list[TemplateView]
    controls_active: list[ActiveControl]
    log: list[LogEntry]
    forecast: Forecast | None
    reminders: list[str]
    command: CommandBrief | None = None


# ---------------------------------------------------------------------------
# 7. Endpoints (CONTRACTS §7): request bodies + misc response shapes
# ---------------------------------------------------------------------------


class ScenarioSummary(BaseModel):
    id: str
    name: str
    description: str
    duration_s: int
    tags_expected: list[Tag]


class TemplateCatalogueEntry(BaseModel):
    id: str
    audience: str
    channel: str
    title: str
    trigger: str


class CatalogueDTO(BaseModel):
    signals: list[SignalDef]
    controls: list[ControlDef]
    templates: list[TemplateCatalogueEntry]


class StartBody(BaseModel):
    scenario_id: str
    speed: float = 8


class ClockBody(BaseModel):
    op: Literal["pause", "resume", "speed", "jump"]
    speed: float | None = None
    t: int | None = None


class AlertAckBody(BaseModel):
    actor: Role


class ActionDecideBody(BaseModel):
    decision: Literal["approve", "skip", "done"]
    actor: Role
    rationale: str | None = None


class TemplateSendBody(BaseModel):
    actor: Role
    text: str


class TemplateDismissBody(BaseModel):
    actor: Role
    rationale: str


class NotesBody(BaseModel):
    actor: Role
    text: str


class SeverityBody(BaseModel):
    sev: SevLevel
    actor: Role
    reason: str


class PendingConfirmBody(BaseModel):
    actor: Literal["IC"]


class LiquidationReviewBody(BaseModel):
    verdict: LiqReview
    actor: Role
    rationale: str


class CopilotBody(BaseModel):
    """A question for the deterministic P2 incident copilot.

    The copilot receives the live, modelled command state server-side.  It
    does not accept client-supplied financial figures.
    """

    question: str


class ExecutionDecisionBody(BaseModel):
    decision: Literal["valid", "investigate", "escalated"]
    actor: Literal["TL"]
    rationale: str | None = None


class QueueRecordBody(BaseModel):
    actor: Literal["TL"]
    event: Literal["opened", "run", "reviewed"]
    rationale: str | None = None


class InjectBody(BaseModel):
    event: Literal["stablecoin_dip", "oracle_stale", "api_overload", "rumour"]


class ErrorDetail(BaseModel):
    detail: str


class PeakEntry(BaseModel):
    signal: str
    value: float
    t: int


class IncidentSummary(BaseModel):
    scenario_id: str
    started_t: int
    ended_t: int | None
    peak_sev: SevLevel
    timeline: list[LogEntry]  # transitions only
    peaks: list[PeakEntry]
    decisions: list[LogEntry]
    comms: list[LogEntry]
    liquidation_reviews: list[LogEntry]
    open_items: list[str]
    markdown: str
