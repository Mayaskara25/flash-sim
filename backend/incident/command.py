"""P2 incident command brief — derived from live session facts, never invented."""

from __future__ import annotations

from .catalogue import SIGNALS, status_of
from .contracts import (
    ActionQueueItem,
    CommandBrief,
    CommandDelta,
    ExecutionView,
    InvestigationCluster,
    TeamMember,
    WhyAlert,
)


_RISK_FROM_STATE = {
    "NORMAL": "NORMAL",
    "WATCH": "WATCH",
    "WARNING": "ACTION",
    "CRITICAL": "CRITICAL",
    "EMERGENCY": "CRITICAL",
    "STABILISING": "WATCH",
    "RESOLVED": "NORMAL",
}

_OWNER = {"IC": "P1", "TL": "P2", "CS": "P3", "system": "SYS"}


def _sig(signals: dict[str, float], code: str, default: float = 0.0) -> float:
    return float(signals.get(code, default))


def _catalog_baseline(code: str) -> float:
    for item in SIGNALS:
        if item.code == code:
            return float(item.baseline)
    return 0.0


def risk_level(state: str) -> str:
    return _RISK_FROM_STATE.get(state, "WATCH")


def modelled_liquidity_change(signals: dict[str, float]) -> float:
    """Estimated liquidity deterioration (%). Negative = thinner book."""
    liq = _sig(signals, "LIQ_RATE", 5.0)
    baseline = max(_catalog_baseline("LIQ_RATE"), 1.0)
    latency = _sig(signals, "ORDER_LATENCY_P95", 80.0)
    rejects = _sig(signals, "LP_REJECT_PCT", 0.5)
    from_liq = min(70.0, max(0.0, (liq / baseline - 1.0) * 8.0))
    from_lat = min(20.0, max(0.0, (latency / 80.0 - 1.0) * 4.0))
    from_lp = min(15.0, max(0.0, rejects * 1.5))
    return -round(min(80.0, from_liq + from_lat + from_lp), 1)


def why_alert(code: str, value: float, baseline: float, watch, warn, critical, unit: str) -> WhyAlert:
    change = None
    if baseline:
        change = round(100.0 * (value - baseline) / abs(baseline), 1)
    conclusion = "Signal is inside its modelled baseline band."
    if status_of(code, value) == "critical":
        conclusion = "This signal has crossed its critical threshold."
    elif status_of(code, value) == "warn":
        conclusion = "This signal is in the warning band and needs operator review."
    elif status_of(code, value) == "watch":
        conclusion = "This signal has left the baseline band."
    return WhyAlert(
        signal=code, value=round(value, 3), baseline=round(baseline, 3),
        watch=watch, warn=warn, critical=critical, unit=unit,
        change_pct=change, conclusion=conclusion,
    )


def build_executions(session, cluster_id: str) -> list[ExecutionView]:
    if not session.started or session.generator is None:
        return []
    book = session.generator.book
    px = float(session.frame.values.get("PX", 0.0))
    fills = list(book.recent_fills)
    if not fills:
        return []
    # Prefer larger modelled-vs-fill deviations (flagged for investigation).
    ranked = []
    for t, idx, thresh, fill, delay in fills[-80:]:
        if thresh == 0:
            continue
        deviation = abs(fill - thresh) / abs(thresh) * 100.0
        ranked.append((deviation, t, idx, thresh, fill, delay))
    ranked.sort(reverse=True)
    picked = ranked[:8]
    out = []
    asset = session.scenario.spec.asset
    stored = session.execution_verdicts
    for deviation, t, idx, thresh, fill, delay in picked:
        # The execution timestamp + synthetic position id is stable across
        # polls. A rank-based id would attach a P2 decision to a different
        # fill after the next simulation tick.
        eid = f"{cluster_id}-{t:04d}-{idx:05d}"
        reasons = ["modelled threshold deviation"]
        if delay >= 400:
            reasons.append("unusual execution timing")
        if len(picked) >= 3:
            reasons.append("similar deviations detected in other positions")
        execution = ExecutionView(
            id=eid, cluster_id=cluster_id, trader_id=f"TR-{48200 + idx % 9000:05d}",
            asset=asset, side="LONG" if bool(book.is_long[idx]) else "SHORT",
            leverage=round(float(book.lev[idx]), 1),
            modelled_threshold=round(float(thresh), 2),
            observed_execution=round(float(fill), 2),
            deviation_pct=round(float(deviation), 2),
            execution_delay_ms=round(float(delay), 0),
            market_price=round(px, 2),
            liquidity_condition="thinner than baseline (modelled)",
            reasons=reasons,
            status=stored.get(eid, "flagged"),
            label="Flagged for investigation — potential anomaly, not proof of an exchange error.",
        )
        # Keep evidence for reviewed executions even when they age out of the
        # live eight-row investigator view; the report uses this ledger.
        session.execution_records[eid] = execution.model_dump()
        out.append(execution)
    return out


def build_cluster(session, executions: list[ExecutionView]) -> InvestigationCluster | None:
    if not executions:
        return None
    t = session.frame.t if session.frame else 0
    cluster_id = "LC-07" if (session.scenario and session.scenario.spec.id == "C1") else f"LC-{(7 + max(t, 0) // 600) % 10:02d}"
    flagged = [e for e in executions if e.status in {"flagged", "investigate"}]
    return InvestigationCluster(
        id=cluster_id,
        asset=executions[0].asset,
        flagged_count=len(flagged) or len(executions),
        executions=executions,
        why="Modelled threshold deviation plus unusual execution timing. Research prototype — flagged for investigation only.",
    )


def _reasons(liq_rate: float, baseline: float, near: int, liq_chg: float, lar: float, tickets: float) -> list[str]:
    ratio = liq_rate / max(baseline, 0.01)
    rows = []
    if ratio >= 1.2:
        rows.append(f"Liquidation rate is {ratio:.1f}× above baseline")
    if near >= 20:
        rows.append(f"{near:,} positions are near modelled liquidation thresholds")
    if liq_chg <= -10:
        rows.append(f"Market liquidity has fallen {abs(liq_chg):.0f}% (modelled)")
    if lar >= 1.5:
        rows.append(f"Liquidation anomaly ratio is {lar:.1f} (above watch)")
    if tickets >= 2:
        rows.append(f"Customer tickets are {tickets:.1f}× baseline")
    if not rows:
        rows.append("No independent risk signal is currently elevated")
    return rows[:3]


def _queue(session, cluster: InvestigationCluster | None, near: int, liq_chg: float) -> list[ActionQueueItem]:
    items: list[ActionQueueItem] = []
    proposed = [a for a in session.actions.values() if a.status == "proposed"]
    proposed.sort(key=lambda a: (a.priority, a.proposed_t))
    if cluster and cluster.flagged_count:
        p2_open = any(a.status in {"proposed", "approved"} and "liquidat" in a.text.lower() and a.role == "TL" for a in session.actions.values())
        items.append(ActionQueueItem(
            id="p2.investigate", band="NOW", owner="P2", role="TL",
            text=f"Investigate liquidation cluster {cluster.id}",
            reason=f"{cluster.flagged_count} executions flagged for investigation",
            status="open" if p2_open or True else "open",
            eta="2 min", button="OPEN", ref=cluster.id, priority=1,
        ))
    tl = [a for a in proposed if a.role == "TL"]
    ic = [a for a in proposed if a.role == "IC"]
    cs = [a for a in proposed if a.role == "CS"]
    exposure = _sig(session.frame.values if session.frame else {}, "NET_EXPOSURE_PCT", 20)
    if exposure >= 50 and not any(i.id == "p2.exposure" for i in items):
        cr = max(0.0, exposure / 100.0 * 165)
        items.append(ActionQueueItem(
            id="p2.exposure", band="NEXT", owner="P2", role="TL",
            text="Review high-leverage exposure",
            reason=f"Modelled ₹{cr:.0f} Cr equivalent at risk (research estimate)",
            status="proposed", eta=None, button="OPEN", ref="exposure", priority=3,
        ))
    if session.started and session.machine.state in {"WARNING", "CRITICAL", "EMERGENCY"}:
        items.append(ActionQueueItem(
            id="p2.stress", band="NEXT", owner="P2", role="TL",
            text="Run −15% stress scenario",
            reason="Compare modelled cascade under a further shock. Human approval required; AI cannot execute controls.",
            status="proposed", eta=None, button="RUN", ref="stress", priority=4,
        ))
    tickets = _sig(session.frame.values if session.frame else {}, "TICKET_RATE", 1)
    if tickets >= 2:
        items.append(ActionQueueItem(
            id="p3.tickets", band="MONITOR", owner="P3", role="CS",
            text="Customer tickets",
            reason=f"+{round((tickets - 1) * 100)}% vs baseline · owner P3",
            status="monitor", eta=None, button=None, ref="tickets", priority=9,
        ))
    # Map remaining playbook actions into bands without duplicating the cluster card.
    for i, action in enumerate(tl[:2]):
        band = "NOW" if i == 0 and not items else "NEXT"
        if items and items[0].id == "p2.investigate" and i == 0:
            band = "NEXT"
        items.append(ActionQueueItem(
            id=action.id, band=band, owner="P2", role="TL", text=action.text,
            reason=action.rationale_hint, status=action.status,
            eta=None, button="APPROVE", ref=action.id, priority=action.priority,
        ))
    for action in ic[:2]:
        items.append(ActionQueueItem(
            id=action.id, band="NEXT" if items else "NOW", owner="P1", role="IC",
            text=action.text, reason=action.rationale_hint, status=action.status,
            eta=None, button="APPROVE", ref=action.id, priority=action.priority,
        ))
    for action in cs[:1]:
        items.append(ActionQueueItem(
            id=action.id, band="MONITOR", owner="P3", role="CS",
            text=action.text, reason=action.rationale_hint, status=action.status,
            eta=None, button="APPROVE", ref=action.id, priority=action.priority,
        ))
    # Keep the operator to a handful of cards.
    now = [x for x in items if x.band == "NOW"][:2]
    nxt = [x for x in items if x.band == "NEXT"][:3]
    mon = [x for x in items if x.band == "MONITOR"][:2]
    return now + nxt + mon


def _team(session) -> list[TeamMember]:
    started = session.started
    sev = session._sev() if started else 4
    tickets = _sig(session.frame.values if session.frame else {}, "TICKET_RATE", 1)
    pending = bool(started and session.machine.pending)
    p1 = "Busy" if pending or (started and sev <= 2) else ("Available" if started else "Standby")
    p2 = "Active" if started and sev <= 3 else ("Available" if started else "Standby")
    p3 = "Busy" if tickets >= 3 else ("Available" if started else "Standby")
    return [
        TeamMember(id="P1", role="IC", title="Incident Commander",
                   status=p1, responsibility="Escalation / overall incident"),
        TeamMember(id="P2", role="TL", title="Risk & Trading",
                   status=p2, responsibility="Liquidations / exposure / anomalies"),
        TeamMember(id="P3", role="CS", title="Customer Operations",
                   status=p3, responsibility="Support / customer communication"),
    ]


def snapshot_facts(session) -> dict:
    if not session.started or session.frame is None:
        return {
            "t": 0, "risk_level": "NORMAL", "cascade_score": 0.0,
            "liquidation_rate": 0.0, "liquidation_baseline": 5.0,
            "near_liquidation": 0, "liquidity_change": 0.0, "lar": 1.0,
        }
    values = session.frame.values
    px_chg = float(session.frame.meta.get("px_eff", 0.0))
    near = 0
    if session.generator is not None:
        near = session.generator.book.near_liquidation_count(px_chg)
    return {
        "t": session.frame.t,
        "risk_level": risk_level(session.machine.state),
        "cascade_score": round(float(session.severity.score if session.severity else 0), 1),
        "liquidation_rate": round(_sig(values, "LIQ_RATE"), 1),
        "liquidation_baseline": _catalog_baseline("LIQ_RATE"),
        "near_liquidation": near,
        "liquidity_change": modelled_liquidity_change(values),
        "lar": round(_sig(values, "LAR", 1.0), 2),
        "tickets": round(_sig(values, "TICKET_RATE", 1.0), 2),
        "exposure_pct": round(_sig(values, "NET_EXPOSURE_PCT", 20), 1),
        "px_chg": round(_sig(values, "PX_CHG_5M"), 2),
        "abnormal_liquidations": 0,
    }


def delta_from(prev: dict | None, cur: dict) -> CommandDelta | None:
    if not prev:
        return None
    dt = max(0, int(cur.get("t", 0)) - int(prev.get("t", 0)))
    lines = []
    def _chg(key, label, unit=""):
        a, b = prev.get(key), cur.get(key)
        if a is None or b is None or a == b:
            return
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            lines.append(f"{label} {a}{unit} → {b}{unit}")
    _chg("liquidation_rate", "liquidation rate", "/min")
    if cur.get("near_liquidation") != prev.get("near_liquidation"):
        diff = int(cur.get("near_liquidation", 0)) - int(prev.get("near_liquidation", 0))
        sign = "+" if diff >= 0 else ""
        lines.append(f"near-liquidation positions {sign}{diff} ({prev.get('near_liquidation')} → {cur.get('near_liquidation')})")
    _chg("liquidity_change", "modelled liquidity", "%")
    _chg("lar", "LAR")
    _chg("tickets", "ticket rate", "×")
    if cur.get("abnormal_liquidations") == prev.get("abnormal_liquidations"):
        lines.append("no new abnormal clusters were detected")
    elif cur.get("abnormal_liquidations") is not None:
        _chg("abnormal_liquidations", "flagged executions")
    if not lines:
        lines.append("no material change in the tracked risk signals")
    minutes = max(1, round(dt / 60)) if dt else 0
    ago = f"{minutes} minute" + ("" if minutes == 1 else "s") if dt else "your last check"
    return CommandDelta(elapsed_s=dt, since_label=ago, lines=lines[:6])


def build_command(session) -> CommandBrief:
    if not session.started or session.frame is None:
        return CommandBrief(
            risk_level="NORMAL", cascade_score=0, incident_mode=False,
            reasons=["Start a scenario to populate the P2 risk brief."],
            first_priority="Start Black Tuesday (C1) from the scenario selector.",
            why_first="No live incident is running.",
            next_step="Select C1 and press Start.",
            liquidation_rate=0, liquidation_baseline=5, near_liquidation=0,
            liquidity_change=0, abnormal_liquidations=0, lar=1, exposure_pct=20,
            px_chg=0, ticket_rate=1, largest_cluster=None, cluster=None,
            queue=[], team=_team(session), delta=None, why_alerts=[],
            label="Simulated research prototype — modelled figures only.",
        )
    values = dict(session.frame.values)
    facts = snapshot_facts(session)
    facts["abnormal_liquidations"] = 0
    cluster_id = "LC-07" if session.scenario.spec.id == "C1" else "LC-07"
    executions = build_executions(session, cluster_id)
    cluster = build_cluster(session, executions)
    facts["abnormal_liquidations"] = cluster.flagged_count if cluster else 0
    liq_rate = facts["liquidation_rate"]
    baseline = facts["liquidation_baseline"]
    near = facts["near_liquidation"]
    liq_chg = facts["liquidity_change"]
    lar = facts["lar"]
    reasons = _reasons(liq_rate, baseline, near, liq_chg, lar, facts.get("tickets", 1))
    if cluster:
        first = f"Investigate liquidation cluster {cluster.id}"
        why_first = "Large concentration of vulnerable positions + abnormal liquidation activity (flagged for investigation)."
        nxt = f"Review {cluster.flagged_count} flagged executions."
    else:
        proposed = [a for a in session.actions.values() if a.status == "proposed"]
        proposed.sort(key=lambda a: a.priority)
        p2 = next((a for a in proposed if a.role == "TL"), None)
        first = p2.text if p2 else (proposed[0].text if proposed else "Monitor signals — no P2 action is queued.")
        why_first = p2.rationale_hint if p2 else "No abnormal liquidation cluster is currently flagged."
        nxt = proposed[1].text if len(proposed) > 1 else "Continue monitoring liquidations and exposure."
    queue = _queue(session, cluster, near, liq_chg)
    why_alerts = []
    for sig in SIGNALS:
        value = values.get(sig.code)
        if value is None:
            continue
        if status_of(sig.code, value) in {"warn", "critical"}:
            why_alerts.append(why_alert(sig.code, value, sig.baseline, sig.watch, sig.warn, sig.critical, sig.unit))
    why_alerts = why_alerts[:6]
    level = facts["risk_level"]
    incident_mode = session.machine.state in {"CRITICAL", "EMERGENCY"}
    prev = session.operator_snapshot
    delta = delta_from(prev, facts)
    return CommandBrief(
        risk_level=level,
        cascade_score=facts["cascade_score"],
        incident_mode=incident_mode,
        reasons=reasons,
        first_priority=first,
        why_first=why_first,
        next_step=nxt,
        liquidation_rate=liq_rate,
        liquidation_baseline=baseline,
        near_liquidation=near,
        liquidity_change=liq_chg,
        abnormal_liquidations=facts["abnormal_liquidations"],
        lar=lar,
        exposure_pct=facts["exposure_pct"],
        px_chg=facts["px_chg"],
        ticket_rate=facts.get("tickets", 1),
        largest_cluster=cluster.id if cluster else None,
        cluster=cluster,
        queue=queue,
        team=_team(session),
        delta=delta,
        why_alerts=why_alerts,
        label="Simulated research prototype — modelled figures only.",
    )


