#!/usr/bin/env python3
"""Generate docs/contracts/fixtures/*.json for the H0 stub.

Tells the C1 "Black Tuesday" story (SPEC §12.2, PLAN §3.9):

    idle -> normal (T-01:00, pre-roll)
         -> warning (T+02:10, tag M1: price -6%, LIQ_RATE crosses 100/min)
         -> critical (T+14:32, tags M1 I1 M2: LIQ_RATE 410/min, fund 40%,
                       reduce-only proposed with a what-if)
         -> stabilising (T+40:10, reduce-only approved ~T+18, pending
                          step-down to Stabilising awaiting IC confirm)
         -> resolved (T+55:00, reduce-only lifted, T12 sent)

Plus a standalone `emergency` variant: the branch from PLAN §3.9 where
reduce-only is *not* approved in time and the insurance fund crosses the
25% hard override around T+24 (SEV-1). It shares its early history with
`critical` but is not chained into `summary_c1.json`, which reflects the
main (contained, peak SEV-2) branch actually demoed.

Run with the backend venv (needs `pydantic`, and this repo's
`backend/incident` package on the path):

    backend/.venv/bin/python docs/contracts/make_fixtures.py

Regenerate this file's output whenever contracts.py or the story below
changes, and re-run `pytest` in `backend/` to validate the fixtures.
"""

from __future__ import annotations

import json
import re
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from incident.catalogue import SIGNALS, status_of  # noqa: E402
from incident.contracts import (  # noqa: E402
    ActionView,
    ActiveControl,
    AlertCard,
    ClassifierBlock,
    CommandBrief,
    CommandDelta,
    Dims,
    Driver,
    EtaEstimate,
    Forecast,
    IncidentStateDTO,
    IncidentSummary,
    InvestigationCluster,
    InsFundPoint,
    LogEntry,
    PeakEntry,
    ActionQueueItem,
    PendingTransition,
    SeverityBlock,
    SevProbPoint,
    SignalView,
    SimBlock,
    TagView,
    TemplateView,
    TeamMember,
    Thresholds,
    WhatIf,
    WhyAlert,
    ExecutionView,
)

FIXTURES_DIR = ROOT / "docs" / "contracts" / "fixtures"

SIGNAL_BY_CODE = {s.code: s for s in SIGNALS}
TAG_NAMES = {
    "M1": "Directional flash crash",
    "M2": "Liquidation cascade drains insurance fund",
    "I1": "Customer panic / information cascade",
}


def t_label(t: int) -> str:
    sign = "-" if t < 0 else "+"
    at = abs(t)
    return f"T{sign}{at // 60:02d}:{at % 60:02d}"


# ---------------------------------------------------------------------------
# Signal values and history
# ---------------------------------------------------------------------------

# Per-state overrides of the catalogue baseline. Codes not listed here stay
# at their catalogue baseline for that state.
STATE_T = {
    "idle": 0,
    "normal": -60,
    "warning": 130,
    "critical": 872,
    "emergency": 1440,
    "stabilising": 2410,
    "resolved": 3300,
}

OVERRIDES: dict[str, dict[str, float]] = {
    "idle": {},
    "normal": {},
    "warning": {
        "PX_CHG_5M": -6.2, "LIQ_RATE": 145, "LAR": 1.1, "INS_FUND_PCT": 97,
        "BAD_DEBT_RATE": 0.05, "TICKET_RATE": 1.4, "SENTIMENT": 0.0,
        "NET_EXPOSURE_PCT": 24,
    },
    "critical": {
        "PX_CHG_5M": -9.8, "LIQ_RATE": 410, "LAR": 1.1, "INS_FUND_PCT": 40,
        "BAD_DEBT_RATE": 0.42, "NEG_BAL_ACCTS": 2, "TICKET_RATE": 4.3,
        "SENTIMENT": -0.38, "NET_EXPOSURE_PCT": 46, "RUMOR_MENTIONS": 3,
    },
    "emergency": {
        "PX_CHG_5M": -11.4, "LIQ_RATE": 520, "LAR": 1.2, "INS_FUND_PCT": 22,
        "BAD_DEBT_RATE": 1.35, "NEG_BAL_ACCTS": 4, "TICKET_RATE": 5.6,
        "SENTIMENT": -0.5, "NET_EXPOSURE_PCT": 58, "RUMOR_MENTIONS": 9,
    },
    "stabilising": {
        "PX_CHG_5M": -2.6, "LIQ_RATE": 55, "LAR": 1.0, "INS_FUND_PCT": 46,
        "BAD_DEBT_RATE": 0.0, "NEG_BAL_ACCTS": 2, "TICKET_RATE": 1.7,
        "SENTIMENT": -0.05, "NET_EXPOSURE_PCT": 30, "RUMOR_MENTIONS": 1,
    },
    "resolved": {
        "PX_CHG_5M": -0.4, "LIQ_RATE": 6, "LAR": 1.0, "INS_FUND_PCT": 61,
        "BAD_DEBT_RATE": 0.0, "NEG_BAL_ACCTS": 0, "TICKET_RATE": 1.1,
        "SENTIMENT": 0.05, "NET_EXPOSURE_PCT": 21, "RUMOR_MENTIONS": 0,
    },
}

ACTIVE_TAGS_BY_STATE = {
    "idle": set(), "normal": set(),
    "warning": {"M1"},
    "critical": {"M1", "I1", "M2"},
    "emergency": {"M1", "I1", "M2"},
    "stabilising": {"M2"},  # M1/I1 no longer active; recovery under M2
    "resolved": set(),  # all tags inactive once resolved
}


def value_for(code: str, state: str) -> float:
    return OVERRIDES[state].get(code, SIGNAL_BY_CODE[code].baseline)


def gen_history(code: str, t_now: int, start_val: float, end_val: float, n: int) -> list[tuple[int, float]]:
    rng = random.Random(f"{code}:{t_now}")
    span = min(600, max(60, t_now)) if t_now > 0 else 60
    t0 = t_now - span
    noise = abs(end_val - start_val) * 0.04 + 0.001
    pts: list[tuple[int, float]] = []
    for i in range(n):
        frac = i / (n - 1) if n > 1 else 1.0
        t = round(t0 + frac * (t_now - t0))
        v = start_val + (end_val - start_val) * frac + rng.uniform(-noise, noise)
        pts.append((t, round(v, 4)))
    pts[-1] = (t_now, round(end_val, 4))
    return pts


def build_signals(state: str, t_now: int, prev_values: dict[str, float]) -> list[SignalView]:
    active_tags = ACTIVE_TAGS_BY_STATE[state]
    views: list[SignalView] = []
    for sig in SIGNALS:
        value = value_for(sig.code, state)
        status = status_of(sig.code, value)
        relevant = status != "normal" or bool(set(sig.tags) & active_tags)
        start_val = prev_values.get(sig.code, sig.baseline)
        n = 24 if relevant else 8
        history = gen_history(sig.code, max(t_now, 0), start_val, value, n)
        span_min = max(1.0, (history[-1][0] - history[0][0]) / 60.0)
        trend = round((history[-1][1] - history[0][1]) / span_min, 4)
        views.append(
            SignalView(
                code=sig.code, label=sig.label, unit=sig.unit, value=value,
                status=status, relevant=relevant, trend_per_min=trend,
                history=history,
                thresholds=Thresholds(watch=sig.watch, warn=sig.warn, critical=sig.critical),
                direction=sig.direction,
            )
        )
    views.sort(key=lambda v: not v.relevant)
    return views


# ---------------------------------------------------------------------------
# Actions (shared registry, sliced per fixture by transition time)
# ---------------------------------------------------------------------------

# (t, status, decided_by, rationale)
ActionDef = dict

ACTIONS: list[ActionDef] = [
    dict(id="a1", tag="M1", role="IC", control_id=None, template_id=None,
         text="Acknowledge Warning alert", priority=1,
         rationale_hint="PX_CHG_5M -6.1%, LIQ_RATE 102/min — confirm and check LAR.",
         transitions=[(0, "proposed", None, None), (20, "done", "IC", "Confirmed sharp move on the primary book; LAR 1.1, nominal.")]),
    dict(id="a2", tag=None, role="TL", control_id=None, template_id=None,
         text="Confirm price feed and liquidation engine health", priority=2,
         rationale_hint="Check ORACLE_AGE, API_ERR_PCT and engine error rate.",
         transitions=[(0, "proposed", None, None), (45, "done", "TL", "ORACLE_AGE 1s, API_ERR_PCT 0.3%, no engine errors.")]),
    dict(id="a3", tag="M1", role="IC", control_id="leverage_cap", template_id=None,
         text="Cap max leverage on new positions (10x -> 3x)", priority=3,
         rationale_hint="LIQ_RATE climbing in line with the move; slow future cascade size.",
         transitions=[(20, "proposed", None, None), (90, "approved", "IC", "Slow future cascade size while liquidations remain market-explained.")]),
    dict(id="a4", tag="M2", role="IC", control_id="reduce_only", template_id=None,
         text="Switch BTC-PERP, ETH-PERP to reduce-only (no new exposure)", priority=1,
         rationale_hint="Insurance fund at 40% and falling ~4%/min; LIQ_RATE 410/min.",
         transitions=[
             (855, "proposed", None, None),
             (1080, "approved", "IC", "Forecast shows P(SEV-1 in 15m) 68% -> 21% with this control; act before the fund crosses 25%."),
             (3280, "done", "IC", "All signals below warn for 15+ minutes; fund stable at 61%. Lifted with IC sign-off."),
         ],
         what_if_from_t=855),
    dict(id="a5", tag="M2", role="TL", control_id=None, template_id=None,
         text="Confirm liquidation engine is not over-firing (rule out P1)", priority=2,
         rationale_hint="LAR steady near 0.7-1.5 through the cascade would rule out an engine bug.",
         transitions=[(855, "proposed", None, None), (1095, "done", "TL", "LAR steady at 1.1 through the cascade; matches the price move.")]),
    dict(id="a9", tag="M2", role="CS", control_id=None, template_id="t3",
         text="Send T3 reduce-only notice (pre-filled)", priority=3,
         rationale_hint="Customers need to know before reduce-only affects them.",
         transitions=[(855, "proposed", None, None), (1090, "done", "CS", "Reduce-only approved; notice sent ahead of it taking effect.")]),
    dict(id="a10", tag="M1", role="CS", control_id=None, template_id="t1",
         text="Send T1 volatility notice (in-app banner)", priority=1,
         rationale_hint="PX_CHG_5M -6% and falling; give users a heads-up on liquidation risk.",
         transitions=[(0, "proposed", None, None), (95, "done", "CS", "Factual volatility notice; no cause named yet.")]),
    dict(id="a11", tag="I1", role="CS", control_id=None, template_id="t11",
         text="Send T11 support FAQ to queue", priority=2,
         rationale_hint="Ticket volume 4x baseline; give Support the top-3 answers.",
         transitions=[(360, "proposed", None, None), (380, "done", "CS", None)]),
    dict(id="a12", tag=None, role="IC", control_id=None, template_id=None,
         text="Sign off final state", priority=1,
         rationale_hint="All signals normal for 15+ minutes; confirm closure.",
         transitions=[(3290, "done", "IC", "All signals normal for 15+ minutes; no open liquidation disputes.")]),
]

ACTION_A6_EMERGENCY = dict(
    id="a6", tag=None, role="IC", control_id=None, template_id=None,
    text="Declare SEV-1 and page founders", priority=1,
    rationale_hint="Insurance fund below the 25% hard override.",
    transitions=[(1400, "done", "IC", "Insurance fund below 25% override; reduce-only was not yet approved.")],
)

WHAT_IF_REDUCE_ONLY = WhatIf(
    control_id="reduce_only", p_sev1_15_before=0.68, p_sev1_15_after=0.21,
    fund_p50_15_before=28, fund_p50_15_after=46,
    text="Approving reduce-only drops P(SEV-1 in 15 min) from 68% to 21% and lifts the fund's 15-min median from 28% to 46%.",
)

# Cap: in the emergency (no-action) branch, these ids never advance past the
# "proposed"/"surfaced" transition at t=855, because reduce-only was never
# approved on that branch.
EMERGENCY_CAP_IDS = {"a4", "a5", "a9"}
EMERGENCY_CAP_T = 855


def build_actions(state: str, t_now: int) -> list[ActionView]:
    if state == "idle":
        return []
    defs = list(ACTIONS)
    if state == "emergency":
        defs = defs + [ACTION_A6_EMERGENCY]

    out: list[ActionView] = []
    for d in defs:
        transitions = d["transitions"]
        if state == "emergency" and d["id"] in EMERGENCY_CAP_IDS:
            transitions = [tr for tr in transitions if tr[0] <= EMERGENCY_CAP_T]
        applicable = [tr for tr in transitions if tr[0] <= t_now]
        if not applicable:
            continue
        proposed_t = transitions[0][0]
        last = applicable[-1]
        _, status, decided_by, rationale = last
        decided_t = last[0] if status != "proposed" else None
        what_if = None
        if d.get("what_if_from_t") is not None and t_now >= d["what_if_from_t"]:
            what_if = WHAT_IF_REDUCE_ONLY
        out.append(
            ActionView(
                id=d["id"], tag=d["tag"], role=d["role"], text=d["text"],
                priority=d["priority"], control_id=d["control_id"], template_id=d["template_id"],
                status=status, proposed_t=proposed_t, decided_t=decided_t,
                decided_by=decided_by, rationale=rationale,
                rationale_hint=d["rationale_hint"], expires_t=None, what_if=what_if,
            )
        )
    return out


def build_controls_active(state: str, t_now: int) -> list[ActiveControl]:
    actions = {a.id: a for a in build_actions(state, t_now)}
    active: list[ActiveControl] = []
    a3 = actions.get("a3")
    if a3 and a3.status == "approved":
        active.append(
            ActiveControl(
                control_id="leverage_cap", label="Max leverage on new positions: 10x -> 3x",
                approved_t=90, approved_by="IC", expires_t=None, params={"max_leverage": 3},
            )
        )
    a4 = actions.get("a4")
    if a4 and a4.status == "approved":
        active.append(
            ActiveControl(
                control_id="reduce_only", label="Reduce-only mode (BTC-PERP, ETH-PERP)",
                approved_t=1080, approved_by="IC", expires_t=None, params={},
            )
        )
    return active


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES: list[dict] = [
    dict(id="t1", tag="M1", audience="Customer", channel="in-app banner", title="Volatility notice",
         text="Markets are moving sharply. NVDA-PERP is down 6.2% in the last 5 minutes. "
              "MochaTrade systems are operating normally. Leveraged positions carry higher "
              "liquidation risk right now; review your margin.",
         missing=[], transitions=[(0, "surfaced", None), (95, "sent", "CS")]),
    dict(id="t2", tag=None, audience="Customer", channel="status page", title="Status page update",
         text="We are investigating elevated liquidation activity affecting BTC-PERP and "
              "ETH-PERP. Your funds remain in your account. Next update by T+30:00.",
         missing=[], transitions=[(850, "surfaced", None), (860, "sent", "CS")]),
    dict(id="t3", tag="M2", audience="Customer", channel="in-app", title="Reduce-only notice",
         text="To protect all users during extreme volatility, BTC-PERP and ETH-PERP are in "
              "reduce-only mode: you can close or reduce positions but not open new ones. We "
              "will lift this once conditions stabilise.",
         missing=[], transitions=[(855, "surfaced", None), (1090, "sent", "CS")]),
    dict(id="t11", tag="I1", audience="Support", channel="canned FAQ", title="Top-3 FAQ",
         text="Top-3 answers auto-built from ticket themes: why was I liquidated, can I "
              "withdraw, is MochaTrade safe.",
         missing=[], transitions=[(360, "surfaced", None), (380, "sent", "CS")]),
    dict(id="t12", tag=None, audience="Customer", channel="resolution notice", title="Resolution notice",
         text="The issue affecting trading and liquidations has been resolved as of T+55:00. "
              "No compensation is required — all liquidations were market-explained. Summary: "
              "a sharp market move triggered elevated liquidations; reduce-only was applied at "
              "T+18:00 and lifted once the insurance fund recovered.",
         missing=[], transitions=[(3290, "surfaced", None), (3300, "sent", "CS")]),
]

TEMPLATE_EMERGENCY_CAP_IDS = {"t3"}


def build_templates(state: str, t_now: int) -> list[TemplateView]:
    if state == "idle":
        return []
    out: list[TemplateView] = []
    for d in TEMPLATES:
        transitions = d["transitions"]
        if state == "emergency" and d["id"] in TEMPLATE_EMERGENCY_CAP_IDS:
            transitions = [tr for tr in transitions if tr[0] <= EMERGENCY_CAP_T]
        applicable = [tr for tr in transitions if tr[0] <= t_now]
        if not applicable:
            continue
        surfaced_t = transitions[0][0]
        last = applicable[-1]
        _, status, approved_by = last
        sent_t = last[0] if status == "sent" else None
        out.append(
            TemplateView(
                id=d["id"], tag=d["tag"], audience=d["audience"], channel=d["channel"],
                title=d["title"], text=d["text"], missing=d["missing"], status=status,
                surfaced_t=surfaced_t, sent_t=sent_t, approved_by=approved_by,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Alerts (hand-set per state — cosmetic collapsed-alert counters)
# ---------------------------------------------------------------------------

ALERTS_BY_STATE: dict[str, list[dict]] = {
    "idle": [],
    "normal": [],
    "warning": [
        dict(id="al-px-warn", signal="PX_CHG_5M", level="warn", count=4, first_t=0, last_t=120, acknowledged_by="IC"),
        dict(id="al-liq-warn", signal="LIQ_RATE", level="warn", count=6, first_t=0, last_t=130, acknowledged_by="IC"),
    ],
    "critical": [
        dict(id="al-px-warn", signal="PX_CHG_5M", level="warn", count=11, first_t=0, last_t=850, acknowledged_by="IC"),
        dict(id="al-liq-warn", signal="LIQ_RATE", level="warn", count=6, first_t=0, last_t=130, acknowledged_by="IC"),
        dict(id="al-liq-crit", signal="LIQ_RATE", level="critical", count=5, first_t=700, last_t=872, acknowledged_by=None),
        dict(id="al-fund-warn", signal="INS_FUND_PCT", level="warn", count=4, first_t=780, last_t=872, acknowledged_by=None),
        dict(id="al-ticket-warn", signal="TICKET_RATE", level="warn", count=3, first_t=360, last_t=850, acknowledged_by="CS"),
    ],
    "emergency": [
        dict(id="al-px-warn", signal="PX_CHG_5M", level="warn", count=14, first_t=0, last_t=1400, acknowledged_by="IC"),
        dict(id="al-liq-warn", signal="LIQ_RATE", level="warn", count=6, first_t=0, last_t=130, acknowledged_by="IC"),
        dict(id="al-liq-crit", signal="LIQ_RATE", level="critical", count=10, first_t=700, last_t=1440, acknowledged_by=None),
        dict(id="al-fund-warn", signal="INS_FUND_PCT", level="warn", count=5, first_t=780, last_t=1300, acknowledged_by=None),
        dict(id="al-fund-crit", signal="INS_FUND_PCT", level="critical", count=3, first_t=1300, last_t=1440, acknowledged_by=None),
        dict(id="al-ticket-warn", signal="TICKET_RATE", level="warn", count=5, first_t=360, last_t=1400, acknowledged_by="CS"),
    ],
    "stabilising": [
        dict(id="al-px-warn", signal="PX_CHG_5M", level="warn", count=11, first_t=0, last_t=850, acknowledged_by="IC"),
        dict(id="al-liq-warn", signal="LIQ_RATE", level="warn", count=6, first_t=0, last_t=130, acknowledged_by="IC"),
        dict(id="al-liq-crit", signal="LIQ_RATE", level="critical", count=5, first_t=700, last_t=872, acknowledged_by="TL"),
        dict(id="al-fund-warn", signal="INS_FUND_PCT", level="warn", count=4, first_t=780, last_t=872, acknowledged_by="IC"),
        dict(id="al-ticket-warn", signal="TICKET_RATE", level="warn", count=3, first_t=360, last_t=850, acknowledged_by="CS"),
    ],
    "resolved": [
        dict(id="al-px-warn", signal="PX_CHG_5M", level="warn", count=11, first_t=0, last_t=850, acknowledged_by="IC"),
        dict(id="al-liq-warn", signal="LIQ_RATE", level="warn", count=6, first_t=0, last_t=130, acknowledged_by="IC"),
        dict(id="al-liq-crit", signal="LIQ_RATE", level="critical", count=5, first_t=700, last_t=872, acknowledged_by="TL"),
        dict(id="al-fund-warn", signal="INS_FUND_PCT", level="warn", count=4, first_t=780, last_t=872, acknowledged_by="IC"),
        dict(id="al-ticket-warn", signal="TICKET_RATE", level="warn", count=3, first_t=360, last_t=850, acknowledged_by="CS"),
    ],
}


def build_alerts(state: str) -> list[AlertCard]:
    return [AlertCard(**d) for d in ALERTS_BY_STATE[state]]


# ---------------------------------------------------------------------------
# Log (chronological main branch; sliced by cutoff t per fixture)
# ---------------------------------------------------------------------------

# (t, type, sev, tags, actor, action, rationale, snapshot, liq_review, approved_by, expires_at, ref)
MAIN_LOG: list[tuple] = [
    (-60, "transition", 4, [], "system", "Incident timer started for scenario C1 'Black Tuesday'.", None, {}, None, None, None, None),
    (0, "transition", 3, ["M1"], "system", "NORMAL -> WARNING (PX_CHG_5M -6.1%, LIQ_RATE 102/min).", None, {"PX_CHG_5M": -6.1, "LIQ_RATE": 102}, None, None, None, None),
    (20, "decision", 3, ["M1"], "IC", "Acknowledged Warning alert.", "Confirmed sharp move on the primary book; LAR 1.1, nominal.", {"PX_CHG_5M": -6.1, "LIQ_RATE": 102, "LAR": 1.1}, "market-explained", "IC", None, "a1"),
    (45, "decision", 3, ["M1"], "TL", "Confirmed price feed and liquidation engine healthy.", "ORACLE_AGE 1s, API_ERR_PCT 0.3%, no engine errors.", {"ORACLE_AGE": 1, "API_ERR_PCT": 0.3}, None, "TL", None, "a2"),
    (90, "decision", 3, ["M1"], "IC", "Approved leverage cap: 10x -> 3x on new positions.", "Slow future cascade size while liquidations remain market-explained.", {"LIQ_RATE": 140, "LAR": 1.1}, None, "IC", None, "a3"),
    (95, "comm", 3, ["M1"], "CS", "Sent T1 volatility notice (in-app banner).", None, {"PX_CHG_5M": -6.2}, None, "CS", None, "t1"),
    (360, "alert", 3, ["M1", "I1"], "system", "Tag I1 added: ticket volume 4.1x baseline.", None, {"TICKET_RATE": 4.1, "SENTIMENT": -0.28}, None, None, None, None),
    (380, "comm", 3, ["M1", "I1"], "CS", "Sent T11 support FAQ (top-3 answers) to queue.", None, {"TICKET_RATE": 4.1}, None, "CS", None, "t11"),
    (840, "alert", 3, ["M1", "I1", "M2"], "system", "Tag M2 added: INS_FUND_PCT 42%, falling.", None, {"INS_FUND_PCT": 42, "BAD_DEBT_RATE": 0.3}, None, None, None, None),
    (850, "transition", 2, ["M1", "I1", "M2"], "system", "WARNING -> CRITICAL (LIQ_RATE 405/min, INS_FUND_PCT 41%).", None, {"LIQ_RATE": 405, "INS_FUND_PCT": 41}, None, None, None, None),
    (855, "decision", 2, ["M1", "I1", "M2"], "IC", "Proposed reduce-only on BTC-PERP, ETH-PERP.", "Insurance fund at 40% and falling ~4%/min; LIQ_RATE 410/min.", {"INS_FUND_PCT": 40, "LIQ_RATE": 410}, None, None, None, "a4"),
    (1080, "decision", 2, ["M1", "I1", "M2"], "IC", "Approved reduce-only on BTC-PERP, ETH-PERP.", "Forecast shows P(SEV-1 in 15m) 68% -> 21% with this control; act before the fund crosses 25%.", {"INS_FUND_PCT": 39, "LIQ_RATE": 398}, None, "IC", None, "a4"),
    (1090, "comm", 2, ["M1", "I1", "M2"], "CS", "Sent T3 reduce-only notice.", None, {"INS_FUND_PCT": 39}, None, "CS", None, "t3"),
    (1095, "decision", 2, ["M1", "I1", "M2"], "TL", "Confirmed liquidation engine is not over-firing (ruled out P1).", "LAR steady at 1.1 through the cascade; matches the price move.", {"LAR": 1.1}, "market-explained", "TL", None, "a5"),
    (2000, "alert", 2, ["M1", "I1", "M2"], "system", "Signals below Warning band; timer started for step-down eligibility.", None, {"LIQ_RATE": 70, "INS_FUND_PCT": 45}, None, None, None, None),
    (2110, "alert", 2, ["M1", "I1", "M2"], "system", "Eligible to step down to Stabilising (5 min below band); awaiting IC confirmation.", None, {"LIQ_RATE": 58, "INS_FUND_PCT": 46}, None, None, None, None),
    (2415, "decision", 2, ["M1", "I1", "M2"], "IC", "Confirmed step-down: CRITICAL -> STABILISING.", "Score has held below the Warning band for 5+ minutes; fund recovering.", {"LIQ_RATE": 56, "INS_FUND_PCT": 46}, None, "IC", None, None),
    (2420, "transition", 2, ["M1", "I1", "M2"], "system", "CRITICAL -> STABILISING.", None, {}, None, None, None, None),
    (3280, "decision", 4, ["M1", "I1", "M2"], "IC", "Lifted reduce-only mode.", "All signals below warn for 15+ minutes; fund stable at 61%.", {"INS_FUND_PCT": 61, "LIQ_RATE": 6}, None, "IC", None, "a4"),
    (3290, "decision", 4, ["M1", "I1", "M2"], "IC", "Confirmed resolution: STABILISING -> RESOLVED.", "All signals normal for 15+ minutes; no open liquidation disputes.", {}, None, "IC", None, None),
    (3295, "transition", 4, ["M1", "I1", "M2"], "system", "STABILISING -> RESOLVED.", None, {}, None, None, None, None),
    (3300, "comm", 4, ["M1", "I1", "M2"], "CS", "Sent T12 resolution notice.", None, {}, None, "CS", None, "t12"),
]

EMERGENCY_LOG_EXTRA: list[tuple] = [
    (1300, "alert", 2, ["M1", "I1", "M2"], "system", "INS_FUND_PCT crossed 25%; hard override imminent.", None, {"INS_FUND_PCT": 26}, None, None, None, None),
    (1400, "transition", 1, ["M1", "I1", "M2"], "system", "CRITICAL -> EMERGENCY (insurance fund below 25% override).", None, {"INS_FUND_PCT": 23}, None, None, None, None),
    (1410, "decision", 1, ["M1", "I1", "M2"], "IC", "Declared SEV-1; paged founders.", "Insurance fund below 25% override; reduce-only was not yet approved.", {"INS_FUND_PCT": 22}, None, "IC", None, "a6"),
]


def build_log(state: str, t_now: int) -> list[LogEntry]:
    if state == "idle":
        return []
    if state == "emergency":
        rows = [r for r in MAIN_LOG if r[0] <= 855] + EMERGENCY_LOG_EXTRA
    else:
        rows = MAIN_LOG
    entries = []
    for i, row in enumerate(rows):
        t, typ, sev, tags, actor, action, rationale, snapshot, liq_review, approved_by, expires_at, ref = row
        if t > t_now:
            continue
        entries.append(
            LogEntry(
                id=i + 1, t=t, t_label=t_label(t), type=typ, sev=sev,
                scenario_tags=tags, actor=actor, action=action, rationale=rationale,
                signal_snapshot=snapshot, liquidation_review=liq_review,
                approved_by=approved_by, expires_at=expires_at, ref=ref,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

TAG_FIRST_T = {"M1": 0, "I1": 360, "M2": 840}


def build_tags(state: str, t_now: int) -> list[TagView]:
    if state in ("idle", "normal"):
        return []
    active = ACTIVE_TAGS_BY_STATE[state]
    seen = {tag for tag, first_t in TAG_FIRST_T.items() if first_t <= t_now}
    sev_now = SEV_BY_STATE.get(state, 4)
    out = []
    for tag in ["M1", "I1", "M2"]:
        if tag not in seen:
            continue
        out.append(
            TagView(
                tag=tag, name=TAG_NAMES[tag], active=tag in active,
                first_t=TAG_FIRST_T[tag], peak_sev=sev_now,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Severity / classifier / forecast per state
# ---------------------------------------------------------------------------

SEV_BY_STATE = {
    "idle": 4, "normal": 4, "warning": 3, "critical": 2,
    "emergency": 1, "stabilising": 2, "resolved": 4,
}
STATE_LABEL = {
    "idle": "NORMAL", "normal": "NORMAL", "warning": "WARNING",
    "critical": "CRITICAL", "emergency": "EMERGENCY",
    "stabilising": "CRITICAL",  # pending step-down to STABILISING, not yet confirmed
    "resolved": "RESOLVED",
}
SCORE_BY_STATE = {
    "idle": 0, "normal": 4, "warning": 32, "critical": 58,
    "emergency": 73, "stabilising": 18, "resolved": 5,
}
DIMS_BY_STATE = {
    "idle": Dims(F=0, B=0, A=0, V=0, R=0),
    "normal": Dims(F=0, B=0, A=0, V=0.3, R=0),
    "warning": Dims(F=3, B=1, A=0, V=3, R=0),
    "critical": Dims(F=3, B=3.5, A=1, V=4.5, R=2),
    "emergency": Dims(F=4, B=5, A=2, V=4, R=2),
    "stabilising": Dims(F=1, B=1.5, A=0, V=1, R=0),
    "resolved": Dims(F=0, B=0, A=0, V=0, R=0),
}
SINCE_T = {
    "idle": 0, "normal": -60, "warning": 0, "critical": 850,
    "emergency": 1400, "stabilising": 850, "resolved": 3295,
}
OVERRIDES_TEXT = {
    "emergency": ["Insurance fund below 25% of its starting balance"],
}


def build_classifier(state: str) -> ClassifierBlock:
    table = {
        "idle": ("NONE", 1.0, 0.0, 0.0, "No incident active."),
        "normal": ("NONE", 1.0, 0.4, 0.4, "Baseline liquidation activity; nothing to classify yet."),
        "warning": ("MARKET", 1.1, 13.2, 12.0, "Liquidations track the price move (LAR 1.1, within the 0.7-1.5 band): market-driven, not a system issue."),
        "critical": ("MARKET", 1.1, 45.1, 41.0, "LAR holds at 1.1 through the cascade: liquidations remain explained by the price move, ruling out P1."),
        "emergency": ("MARKET", 1.2, 58.0, 48.0, "Still market-explained (LAR 1.2), but the insurance fund has crossed the SEV-1 override regardless of cause."),
        "stabilising": ("MARKET", 1.0, 6.0, 6.0, "Liquidation rate back near baseline; LAR nominal."),
        "resolved": ("MARKET", 1.0, 1.0, 1.0, "Incident closed. Liquidations throughout were market-explained (LAR 0.9-1.2); no compensation review required."),
    }
    verdict, lar, l_obs, l_exp, explanation = table[state]
    return ClassifierBlock(verdict=verdict, lar=lar, l_obs=l_obs, l_exp=l_exp, explanation=explanation)


def build_forecast(state: str, t_now: int) -> Forecast | None:
    if state == "critical":
        return Forecast(
            computed_t=t_now, horizon_min=[5, 10, 15], n_paths=200,
            sev_probs=[
                SevProbPoint(h=5, p={"1": 0.15, "2": 0.55, "3": 0.2, "4": 0.1}),
                SevProbPoint(h=10, p={"1": 0.35, "2": 0.45, "3": 0.15, "4": 0.05}),
                SevProbPoint(h=15, p={"1": 0.42, "2": 0.4, "3": 0.13, "4": 0.05}),
            ],
            eta_sev1_min=EtaEstimate(p50=9, p90=22, prob_within_15=0.68),
            ins_fund=[
                InsFundPoint(h=5, p10=30, p50=35, p90=38),
                InsFundPoint(h=10, p10=20, p50=30, p90=36),
                InsFundPoint(h=15, p10=10, p50=28, p90=34),
            ],
            eta_fund_25_min=EtaEstimate(p50=11, p90=19, prob_within_15=0.55),
            drivers=[
                Driver(signal="LIQ_RATE", contribution=0.42, text="Liquidation rate climbing fast"),
                Driver(signal="INS_FUND_PCT", contribution=0.33, text="Fund draining roughly 4%/min"),
                Driver(signal="TICKET_RATE", contribution=0.11, text="Ticket surge adding pressure to ops"),
            ],
            cascade_model_p=0.71,
            headline="SEV-1 likely in ~9 min (p 0.68) if reduce-only is not approved",
        )
    if state == "emergency":
        return Forecast(
            computed_t=t_now, horizon_min=[5, 10, 15], n_paths=200,
            sev_probs=[
                SevProbPoint(h=5, p={"1": 0.95, "2": 0.05, "3": 0.0, "4": 0.0}),
                SevProbPoint(h=10, p={"1": 0.97, "2": 0.03, "3": 0.0, "4": 0.0}),
                SevProbPoint(h=15, p={"1": 0.98, "2": 0.02, "3": 0.0, "4": 0.0}),
            ],
            eta_sev1_min=EtaEstimate(p50=0, p90=0, prob_within_15=1.0),
            ins_fund=[
                InsFundPoint(h=5, p10=14, p50=19, p90=23),
                InsFundPoint(h=10, p10=9, p50=15, p90=20),
                InsFundPoint(h=15, p10=4, p50=12, p90=18),
            ],
            eta_fund_25_min=EtaEstimate(p50=None, p90=None, prob_within_15=0.0),
            drivers=[
                Driver(signal="INS_FUND_PCT", contribution=0.48, text="Fund already below the 25% override"),
                Driver(signal="LIQ_RATE", contribution=0.31, text="Liquidations still accelerating"),
                Driver(signal="BAD_DEBT_RATE", contribution=0.14, text="Bad debt compounding the draw"),
            ],
            cascade_model_p=0.94,
            headline="SEV-1 confirmed — insurance fund at 22% and ADL risk rising",
        )
    return None


def build_reminders(state: str, t_now: int) -> list[str]:
    if state == "critical":
        return ["Customer update overdue (last T+01:35)"]
    if state == "emergency":
        return [
            "Customer update overdue (last T+01:35)",
            "Reduce-only still not approved — insurance fund below the SEV-1 override",
        ]
    return []


def build_pending(state: str, t_now: int) -> PendingTransition | None:
    if state == "stabilising":
        return PendingTransition(
            kind="stepdown", **{"from": "CRITICAL"}, to="STABILISING",
            eligible_since_t=2110, needs="IC",
        )
    return None


def build_command(state: str, signals: list[SignalView], actions: list[ActionView]) -> CommandBrief:
    """Fixture-side P2 brief so mock mode exercises the full command UI."""
    values = {signal.code: signal.value for signal in signals}
    risk = {"idle": "NORMAL", "normal": "NORMAL", "warning": "ACTION", "critical": "CRITICAL",
            "emergency": "CRITICAL", "stabilising": "WATCH", "resolved": "NORMAL"}[state]
    liq = values["LIQ_RATE"]
    baseline = SIGNAL_BY_CODE["LIQ_RATE"].baseline
    liquidity = -round(min(80, max(0, (liq / baseline - 1) * 8)), 1)
    near = {"idle": 0, "normal": 0, "warning": 420, "critical": 1847, "emergency": 2411,
            "stabilising": 310, "resolved": 0}[state]
    has_cluster = state in {"critical", "emergency", "stabilising"}
    executions: list[ExecutionView] = []
    if has_cluster:
        for index in range(1, 9):
            threshold = 137.20 + index * 0.14
            observed = threshold * (1 + (0.0138 if index % 2 else -0.0112))
            executions.append(ExecutionView(
                id=f"LC-07-{index:02d}", cluster_id="LC-07", trader_id=f"TR-{48290 + index:05d}",
                asset="NVDA", side="LONG" if index % 3 else "SHORT", leverage=18 - (index % 4),
                modelled_threshold=round(threshold, 2), observed_execution=round(observed, 2),
                deviation_pct=round(abs(observed - threshold) / threshold * 100, 2),
                execution_delay_ms=840 if index < 4 else 480, market_price=round(observed, 2),
                liquidity_condition="thinner than baseline (modelled)",
                reasons=["modelled threshold deviation", "unusual execution timing", "similar deviations detected in other positions"],
                status="flagged", label="Flagged for investigation — potential anomaly, not proof of an exchange error."))
    cluster = InvestigationCluster(id="LC-07", asset="NVDA", flagged_count=len(executions), executions=executions,
                                   why="Modelled threshold deviation plus unusual execution timing. Research prototype — flagged for investigation only.") if executions else None
    reasons = []
    if liq > baseline: reasons.append(f"Liquidation rate is {liq / baseline:.1f}x above baseline")
    if near: reasons.append(f"{near:,} positions are near modelled liquidation thresholds")
    if liquidity <= -10: reasons.append(f"Market liquidity has fallen {abs(liquidity):.0f}% (modelled)")
    if not reasons: reasons.append("No independent risk signal is currently elevated")
    queue: list[ActionQueueItem] = []
    if cluster:
        queue.append(ActionQueueItem(id="p2.investigate", band="NOW", owner="TL", role="TL",
                     text="Investigate liquidation cluster LC-07", reason="8 executions flagged for investigation", status="open", eta="2 min", button="OPEN", ref="LC-07", priority=1))
    if values["NET_EXPOSURE_PCT"] >= 40:
        queue.append(ActionQueueItem(id="p2.exposure", band="NEXT", owner="TL", role="TL",
                     text="Review high-leverage exposure", reason="Modelled exposure above the review band", status="proposed", eta=None, button="OPEN", ref="exposure", priority=3))
    if state in {"warning", "critical", "emergency"}:
        queue.append(ActionQueueItem(id="p2.stress", band="NEXT", owner="TL", role="TL",
                     text="Run -15% stress scenario", reason="Modelled analysis only; human approval remains required for controls.", status="proposed", eta=None, button="RUN", ref="stress", priority=4))
    if values["TICKET_RATE"] >= 2:
        queue.append(ActionQueueItem(id="p3.tickets", band="MONITOR", owner="CS", role="CS",
                     text="Customer tickets", reason=f"+{round((values['TICKET_RATE'] - 1) * 100)}% vs baseline", status="monitor", eta=None, button=None, ref="tickets", priority=9))
    queue = queue[:5]
    team = [
        TeamMember(id="IC", role="IC", title="Incident Commander", status="Busy" if risk == "CRITICAL" else "Available", responsibility="Escalation / overall incident"),
        TeamMember(id="TL", role="TL", title="Tech Lead", status="Active" if state not in {"idle", "normal", "resolved"} else "Available", responsibility="Liquidations / exposure / anomalies"),
        TeamMember(id="CS", role="CS", title="Comms / Support", status="Busy" if values["TICKET_RATE"] >= 3 else "Available", responsibility="Support / customer communication"),
    ]
    why_alerts = [WhyAlert(signal=s.code, value=s.value, baseline=SIGNAL_BY_CODE[s.code].baseline,
                  watch=s.thresholds.watch, warn=s.thresholds.warn, critical=s.thresholds.critical, unit=s.unit,
                  change_pct=round((s.value - SIGNAL_BY_CODE[s.code].baseline) / max(abs(SIGNAL_BY_CODE[s.code].baseline), 1) * 100, 1),
                  conclusion="This signal is outside its modelled baseline band.") for s in signals if s.status in {"warn", "critical"}][:6]
    # H14: a market-driven phase leads with the protective control, not the
    # forensic cluster review. Mirrors backend/incident/command.py::_headline.
    proposed = [a for a in actions if a.status == "proposed"]
    protective = next((a for a in sorted(proposed, key=lambda a: a.priority) if a.control_id), None)
    fund = values["INS_FUND_PCT"]
    if protective is not None and (state in {"critical", "emergency"} or fund <= 95):
        first = protective.text
        why_first = (f"Market-driven (LAR {values['LAR']:.1f}). Insurance fund {fund:.0f}% and falling. "
                     "Flagged fills are secondary evidence — stop new exposure first.")
        others = [a for a in proposed if a is not protective and not re.match(r"^(acknowledge|ack |monitor|watch )", a.text.strip(), re.I)]
        nxt = others[0].text if others else f"Review {len(executions)} flagged executions in Details > Liquidations."
    elif cluster:
        first = "Investigate liquidation cluster LC-07"
        why_first = "Large concentration of vulnerable positions plus abnormal liquidation activity (flagged for investigation)."
        nxt = f"Review {len(executions)} flagged executions."
    else:
        first = "Monitor the modelled incident signals."
        why_first = "No abnormal liquidation cluster is currently flagged."
        nxt = "Continue monitoring the action queue."
    return CommandBrief(risk_level=risk, cascade_score=SCORE_BY_STATE[state], incident_mode=risk == "CRITICAL",
        reasons=reasons[:3], first_priority=first,
        why_first=why_first,
        next_step=nxt,
        liquidation_rate=liq, liquidation_baseline=baseline, near_liquidation=near, liquidity_change=liquidity,
        abnormal_liquidations=len(executions), lar=values["LAR"], exposure_pct=values["NET_EXPOSURE_PCT"],
        px_chg=values["PX_CHG_5M"], ticket_rate=values["TICKET_RATE"], largest_cluster="LC-07" if cluster else None,
        cluster=cluster, queue=queue, team=team, delta=None, why_alerts=why_alerts)


# ---------------------------------------------------------------------------
# Build one IncidentStateDTO
# ---------------------------------------------------------------------------

def build_state(state: str, prev_values: dict[str, float]) -> IncidentStateDTO:
    t_now = STATE_T[state]
    started = state != "idle"
    running = state not in ("idle", "resolved")
    sim = SimBlock(
        scenario_id="C1" if started else None,
        scenario_name="Black Tuesday" if started else None,
        t=t_now, t_label=t_label(t_now), speed=8 if running else 0,
        running=running, duration_s=3600 if started else 0, started=started,
    )
    severity = SeverityBlock(
        state=STATE_LABEL[state], sev=SEV_BY_STATE[state], score=SCORE_BY_STATE[state],
        dims=DIMS_BY_STATE[state], overrides=OVERRIDES_TEXT.get(state, []),
        since_t=SINCE_T[state], pending=build_pending(state, t_now),
    )
    signals = build_signals(state, t_now, prev_values)
    actions = build_actions(state, t_now)
    return IncidentStateDTO(
        sim=sim, severity=severity, classifier=build_classifier(state),
        tags=build_tags(state, t_now), signals=signals,
        alerts=build_alerts(state), actions=actions,
        templates=build_templates(state, t_now), controls_active=build_controls_active(state, t_now),
        log=build_log(state, t_now), forecast=build_forecast(state, t_now),
        reminders=build_reminders(state, t_now), command=build_command(state, signals, actions),
    )


# ---------------------------------------------------------------------------
# Summary (built from the main contained branch: idle..resolved, NOT emergency)
# ---------------------------------------------------------------------------

def build_summary() -> IncidentSummary:
    full_log = build_log("resolved", STATE_T["resolved"])
    timeline = [e for e in full_log if e.type == "transition"]
    decisions = [e for e in full_log if e.type == "decision"]
    comms = [e for e in full_log if e.type == "comm"]
    liquidation_reviews = [e for e in full_log if e.liquidation_review is not None]
    peaks = [
        PeakEntry(signal="LIQ_RATE", value=410, t=872),
        PeakEntry(signal="INS_FUND_PCT", value=38, t=900),
        PeakEntry(signal="PX_CHG_5M", value=-9.8, t=850),
        PeakEntry(signal="TICKET_RATE", value=4.3, t=872),
        PeakEntry(signal="LAR", value=1.2, t=900),
    ]
    markdown = f"""# Incident Summary — C1 "Black Tuesday"

**Scenario:** C1 · **Started:** T-01:00 · **Ended:** T+55:00 · **Peak severity:** SEV-2 Critical

## Timeline
{chr(10).join(f"- {e.t_label} — {e.action}" for e in timeline)}

## Peaks
{chr(10).join(f"- {p.signal}: {p.value} at {t_label(p.t)}" for p in peaks)}

## Decisions
{chr(10).join(f"- {e.t_label} ({e.actor}): {e.action} — {e.rationale}" for e in decisions)}

## Comms sent
{chr(10).join(f"- {e.t_label} ({e.actor}): {e.action}" for e in comms)}

## Liquidation reviews
{chr(10).join(f"- {e.t_label}: {e.liquidation_review}" for e in liquidation_reviews) or "- None disputed; all liquidations market-explained."}

## Open items
- Compensation review: none needed — liquidations market-explained throughout.
"""
    return IncidentSummary(
        scenario_id="C1", started_t=-60, ended_t=3300, peak_sev=2,
        timeline=timeline, peaks=peaks, decisions=decisions, comms=comms,
        liquidation_reviews=liquidation_reviews,
        open_items=["Compensation review: none needed — liquidations market-explained throughout."],
        markdown=markdown,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    gitkeep = FIXTURES_DIR / ".gitkeep"
    if gitkeep.exists():
        gitkeep.unlink()

    order = ["idle", "normal", "warning", "critical", "stabilising", "resolved"]
    prev_values: dict[str, float] = {s.code: s.baseline for s in SIGNALS}

    for state in order:
        dto = build_state(state, prev_values)
        prev_values = {sv.code: sv.value for sv in dto.signals}
        out = FIXTURES_DIR / f"state_{state}.json"
        out.write_text(json.dumps(dto.model_dump(mode="json", by_alias=True), indent=2) + "\n")
        print(f"wrote {out.relative_to(ROOT)}")

    # emergency is a standalone variant branching off the critical snapshot's
    # signal history, not chained into prev_values above.
    critical_values = {s.code: value_for(s.code, "critical") for s in SIGNALS}
    dto = build_state("emergency", critical_values)
    out = FIXTURES_DIR / "state_emergency.json"
    out.write_text(json.dumps(dto.model_dump(mode="json", by_alias=True), indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")

    summary = build_summary()
    out = FIXTURES_DIR / "summary_c1.json"
    out.write_text(json.dumps(summary.model_dump(mode="json", by_alias=True), indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
