"""STUB — replaced in H5.

Every endpoint in CONTRACTS.md §7 exists here and returns real, contract-
valid JSON, but there is no clock, rules engine, or per-operator session
yet: `GET /state` just returns a pointer into the hand-written fixtures in
`docs/contracts/fixtures/`, and every POST (other than `/reset`) advances
that pointer to the "next" fixture in the C1 sequence so the frontend
(H4/H6) has something to click through end to end from day one (PLAN.md
M0). `/start` jumps to `normal`; `/inject` jumps to the standalone
`emergency` variant (fund at 22%, SEV-1 override) to exercise that UI
state; any other action then resumes the regular sequence from wherever it
left off. None of this endpoint logic is real: no validation beyond the
`422` rationale check CONTRACTS calls out, no per-action/template
book-keeping, no actual clock. H5 replaces the whole module with a real
`IncidentSession`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from .catalogue import SIGNALS
from .contracts import (
    ActionDecideBody,
    AlertAckBody,
    CatalogueDTO,
    ClockBody,
    ControlDef,
    IncidentStateDTO,
    IncidentSummary,
    InjectBody,
    LiquidationReviewBody,
    NotesBody,
    PendingConfirmBody,
    ScenarioSummary,
    SeverityBody,
    StartBody,
    TemplateCatalogueEntry,
    TemplateDismissBody,
    TemplateSendBody,
)

router = APIRouter()

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "fixtures"

# The linear "click through the demo" sequence. `emergency` is a standalone
# variant (see docs/contracts/make_fixtures.py) reachable only via /inject.
_SEQUENCE = ["idle", "normal", "warning", "critical", "stabilising", "resolved"]


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURES_DIR / f"state_{name}.json").read_text())


_STATE_FIXTURES: dict[str, dict[str, Any]] = {name: _load_fixture(name) for name in _SEQUENCE}
_STATE_FIXTURES["emergency"] = _load_fixture("emergency")
_SUMMARY_FIXTURE: dict[str, Any] = json.loads((_FIXTURES_DIR / "summary_c1.json").read_text())


class _StubSession:
    """The stub's only state: a pointer into the fixture sequence.

    Not thread-safe and not per-operator — fine for a single local
    dev/demo stub. Replaced in H5 by the real incident session.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._index = 0
        self._override: str | None = None

    def current(self) -> dict[str, Any]:
        name = self._override or _SEQUENCE[self._index]
        return _STATE_FIXTURES[name]

    def start(self) -> dict[str, Any]:
        self._override = None
        self._index = 1  # "normal"
        return self.current()

    def advance(self) -> dict[str, Any]:
        self._override = None
        self._index = min(self._index + 1, len(_SEQUENCE) - 1)
        return self.current()

    def inject(self) -> dict[str, Any]:
        self._override = "emergency"
        return self.current()


_SESSION = _StubSession()


# SPEC.md §8 (compound scenarios). C1 is the built demo spine (H0); C2-C6
# descriptions/tags are carried here so /scenarios is fully populated for
# the frontend scenario picker even before H8 builds their content.
_SCENARIOS: list[ScenarioSummary] = [
    ScenarioSummary(
        id="C1", name="Black Tuesday",
        description="M1 at T+0 -> I1 at T+6 -> M2 at T+14 (fund to 40%) -> reduce-only at T+18 -> recovery from T+35 -> resolved T+55.",
        duration_s=3600, tags_expected=["M1", "I1", "M2"],
    ),
    ScenarioSummary(
        id="C2", name="Depeg spiral",
        description="S1 at T+0 -> collateral haircut triggers liquidations (M2-like) -> I2 insolvency rumours -> S4 withdrawal run.",
        duration_s=3600, tags_expected=["S1", "I2", "S4"],
    ),
    ScenarioSummary(
        id="C3", name="Is it us or the market?",
        description="Mild market dip (-2%) with LAR 3.5 -> P1 liquidation engine bug.",
        duration_s=3600, tags_expected=["M1", "P1"],
    ),
    ScenarioSummary(
        id="C4", name="Can't get out",
        description="M1 -> P2 overload -> liquidations during degradation -> R1 UPI failures stop margin top-ups.",
        duration_s=3600, tags_expected=["M1", "P2", "R1"],
    ),
    ScenarioSummary(
        id="C5", name="Naked book",
        description="M1 -> S3 LP outage -> net exposure breach -> M5 if the options book exists.",
        duration_s=3600, tags_expected=["M1", "S3", "M5"],
    ),
    ScenarioSummary(
        id="C6", name="Bad actor",
        description="M1 + I1 -> P3 unusual hot-wallet outflow during the withdrawal surge.",
        duration_s=3600, tags_expected=["M1", "I1", "P3"],
    ),
]

# SPEC.md §9.4 (protective controls). Effects/params are H3's job; the
# stub only needs id/label/reduces/tradeoff/tags/time_box_s to exist.
_CONTROLS: list[ControlDef] = [
    ControlDef(id="leverage_cap", label="Lower max leverage on new positions", reduces="Future cascade size", tradeoff="Revenue, user complaints", tags=["M1", "M2"], time_box_s=None, effects=[], params={}),
    ControlDef(id="reduce_only", label="Reduce-only mode per instrument", reduces="New exposure, hedge gap", tradeoff="Users cannot open trades", tags=["M2", "S3", "P1"], time_box_s=None, effects=[], params={}),
    ControlDef(id="raise_mm", label="Raise maintenance margin / partial liquidation", reduces="Cascade speed", tradeoff="More margin calls", tags=["M2", "M6"], time_box_s=None, effects=[], params={}),
    ControlDef(id="pause_liqs", label="Pause liquidations (time-boxed)", reduces="Wrongful liquidations", tradeoff="Bad debt grows while paused", tags=["M4", "P1", "P2"], time_box_s=600, effects=[], params={}),
    ControlDef(id="fallback_feed", label="Switch to fallback price feed", reduces="Bad marks", tradeoff="Slight lag", tags=["M4"], time_box_s=None, effects=[], params={}),
    ControlDef(id="collateral_haircut", label="Collateral haircut policy", reduces="Treasury gap in depeg", tradeoff="Some users liquidated", tags=["S1"], time_box_s=None, effects=[], params={}),
    ControlDef(id="pause_deposits", label="Pause deposits in one asset", reduces="Toxic inflows", tradeoff="Users cannot top up in that coin", tags=["S1", "S2"], time_box_s=None, effects=[], params={}),
    ControlDef(id="ins_fund_topup", label="Insurance fund top-up", reduces="ADL risk", tradeoff="Uses company capital", tags=["M2", "M3"], time_box_s=None, effects=[], params={}),
    ControlDef(id="load_shed", label="Load shedding", reduces="Engine overload", tradeoff="Non-core features offline", tags=["P2"], time_box_s=None, effects=[], params={}),
    ControlDef(id="freeze_hot_wallet", label="Freeze hot-wallet signing", reduces="Theft", tradeoff="All withdrawals stop", tags=["P3"], time_box_s=None, effects=[], params={}),
]

# SPEC.md §11 (communication templates T1-T12).
_TEMPLATES_CATALOGUE: list[TemplateCatalogueEntry] = [
    TemplateCatalogueEntry(id="t1", audience="Customer", channel="in-app banner", title="Volatility notice", trigger="M1 at Warning"),
    TemplateCatalogueEntry(id="t2", audience="Customer", channel="status page", title="Status page update", trigger="Any SEV-2+ confirmed"),
    TemplateCatalogueEntry(id="t3", audience="Customer", channel="in-app", title="Reduce-only notice", trigger="M2 reduce-only activated"),
    TemplateCatalogueEntry(id="t4", audience="Customer", channel="in-app + email", title="Liquidation pause notice", trigger="M4 or P1 liquidation pause"),
    TemplateCatalogueEntry(id="t5", audience="Customer", channel="asset notice", title="Stablecoin depeg notice", trigger="S1 depeg"),
    TemplateCatalogueEntry(id="t6", audience="Customer", channel="withdrawal screen", title="Withdrawal delay notice", trigger="S4, S2, R1"),
    TemplateCatalogueEntry(id="t7", audience="Customer", channel="security", title="Security notice", trigger="I2 or P3"),
    TemplateCatalogueEntry(id="t8", audience="Internal", channel="incident channel", title="Internal escalation", trigger="Any transition"),
    TemplateCatalogueEntry(id="t9", audience="Partner", channel="direct ops channel", title="Partner status request", trigger="S2, S3, R1 when a dependency is implicated"),
    TemplateCatalogueEntry(id="t10", audience="Public", channel="official X account", title="Public statement", trigger="SEV-1, after founder approval"),
    TemplateCatalogueEntry(id="t11", audience="Support", channel="canned FAQ", title="Top-3 FAQ", trigger="I1 at Warning"),
    TemplateCatalogueEntry(id="t12", audience="Customer", channel="resolution notice", title="Resolution notice", trigger="State -> Resolved"),
]


@router.get("/scenarios", response_model=list[ScenarioSummary])
def get_scenarios() -> list[ScenarioSummary]:
    return _SCENARIOS


@router.get("/catalogue", response_model=CatalogueDTO)
def get_catalogue() -> CatalogueDTO:
    return CatalogueDTO(signals=SIGNALS, controls=_CONTROLS, templates=_TEMPLATES_CATALOGUE)


@router.post("/start", response_model=IncidentStateDTO)
def start(body: StartBody) -> dict[str, Any]:
    return _SESSION.start()


@router.post("/clock", response_model=IncidentStateDTO)
def clock(body: ClockBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/reset", response_model=IncidentStateDTO)
def reset() -> dict[str, Any]:
    _SESSION.reset()
    return _SESSION.current()


@router.get("/state", response_model=IncidentStateDTO)
def get_state() -> dict[str, Any]:
    return _SESSION.current()


@router.post("/alerts/{alert_id}/ack", response_model=IncidentStateDTO)
def ack_alert(alert_id: str, body: AlertAckBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/actions/{action_id}/decide", response_model=IncidentStateDTO)
def decide_action(action_id: str, body: ActionDecideBody) -> dict[str, Any]:
    if body.decision in ("approve", "skip") and not body.rationale:
        raise HTTPException(status_code=422, detail="rationale is required for approve/skip")
    return _SESSION.advance()


@router.post("/templates/{template_id}/send", response_model=IncidentStateDTO)
def send_template(template_id: str, body: TemplateSendBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/templates/{template_id}/dismiss", response_model=IncidentStateDTO)
def dismiss_template(template_id: str, body: TemplateDismissBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/notes", response_model=IncidentStateDTO)
def add_note(body: NotesBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/severity", response_model=IncidentStateDTO)
def set_severity(body: SeverityBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/pending/confirm", response_model=IncidentStateDTO)
def confirm_pending(body: PendingConfirmBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/liquidations/review", response_model=IncidentStateDTO)
def review_liquidation(body: LiquidationReviewBody) -> dict[str, Any]:
    return _SESSION.advance()


@router.post("/inject", response_model=IncidentStateDTO)
def inject(body: InjectBody) -> dict[str, Any]:
    return _SESSION.inject()


@router.get("/summary", response_model=IncidentSummary)
def get_summary() -> dict[str, Any]:
    return _SUMMARY_FIXTURE
