"""Live-state P2 response generator.

This is deliberately a bounded incident-response generator rather than a
generic chat model. It interprets a question, retrieves relevant evidence
from the current synthetic run and its snapshots, then composes a concise
answer. Every number comes from the simulation state or audit journal.
"""

from __future__ import annotations

import re

from .command import build_command, delta_from, snapshot_facts
from .contracts import CopilotReply
from .log import time_label


_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "ten": 10, "fifteen": 15, "thirty": 30, "sixty": 60,
}


def _window_seconds(question: str) -> int | None:
    """Read a natural request such as 'last five minutes' or 'past 10m'."""
    query = question.lower()
    match = re.search(r"(?:last|past|previous)\s+(\d+|[a-z]+)\s*(?:minutes?|mins?|m)\b", query)
    if not match:
        return None
    value = match.group(1)
    minutes = int(value) if value.isdigit() else _NUMBER_WORDS.get(value)
    return minutes * 60 if minutes else None


def _intent(question: str) -> str:
    """Classify operational intent without requiring a fixed canned phrase."""
    query = question.lower()
    rules = (
        ("change", ("change", "since", "last ", "past ", "delta", "different")),
        ("priority", ("first", "priority", "do now", "should i do", "what do i do")),
        ("risk", ("risk", "critical", "severity", "why is", "biggest")),
        ("execution", ("flag", "execution", "liquidation", "cluster", "threshold", "delay")),
        ("exposure", ("exposure", "at risk", "gross", "net", "leverage")),
        ("stress", ("stress", "scenario", "further shock", "15%")),
        ("actions", ("action", "queue", "next step", "owner", "who should")),
        ("team", ("team", "p1", "p2", "p3", "available", "busy")),
        ("communications", ("customer", "support", "communication", "notice", "message")),
        ("status", ("status", "summary", "resolved", "end", "finish")),
        ("brief", ("brief", "overview", "happening", "update")),
    )
    for intent, terms in rules:
        if any(term in query for term in terms):
            return intent
    return "brief"


def _current_facts(session, command) -> dict[str, float | int | str | None]:
    values = session.frame.values if session.started and session.frame else {}
    fund = float(values.get("INS_FUND_PCT", 100.0))
    facts = snapshot_facts(session)
    facts.update({
        "scenario": session.scenario.spec.name if session.started else None,
        "sim_time": time_label(session.frame.t) if session.started and session.frame else "T+00:00",
        "incident_state": session.machine.state if session.started else "IDLE",
        "price_change_5m": round(float(values.get("PX_CHG_5M", 0.0)), 2),
        "insurance_fund_pct": round(fund, 1),
        "active_controls": len(session.controls),
        "decisions_recorded": sum(1 for entry in session.journal.entries if entry.type == "decision"),
        "communications_sent": sum(1 for entry in session.journal.entries if entry.type == "comm"),
        "abnormal_liquidations": command.abnormal_liquidations,
        "largest_cluster": command.largest_cluster,
    })
    return facts


def _window_delta(session, facts: dict, requested_window_s: int | None):
    if not session.started or session.frame is None:
        return None
    reference = None
    if requested_window_s:
        target = session.frame.t - requested_window_s
        eligible = [item for item in session.p2_snapshots if item.get("t", 0) <= target]
        if eligible:
            reference = eligible[-1]
    else:
        reference = session.operator_snapshot
        if reference is None:
            eligible = [item for item in session.p2_snapshots if item.get("t", 0) <= session.frame.t - 300]
            reference = eligible[-1] if eligible else None
    return delta_from(reference, facts) if reference else None


def _execution_evidence(command) -> str:
    if not command.cluster or not command.cluster.executions:
        return "No modelled abnormal execution is currently in the investigator queue."
    execution = next((item for item in command.cluster.executions if item.status in {"flagged", "investigate"}), command.cluster.executions[0])
    reasons = ", ".join(execution.reasons[:2])
    return (
        f"{execution.id} is {execution.status} because its modelled threshold deviation is "
        f"{execution.deviation_pct:.2f}% with a {execution.execution_delay_ms:.0f} ms execution delay; "
        f"evidence includes {reasons}. This is a potential anomaly, not proof of an exchange or system error."
    )


def _queue_text(command) -> str:
    if not command.queue:
        return "No P2 action is currently queued. Continue monitoring the modelled signals."
    items = [f"{item.band}: {item.text} ({item.owner})" for item in command.queue[:3]]
    return "Current queue: " + "; ".join(items) + "."


def _communication_text(session, command) -> str:
    sent = [item for item in session.templates.values() if item.status == "sent"]
    surfaced = [item for item in session.templates.values() if item.status == "surfaced"]
    if sent:
        latest = sent[-1]
        return f"{len(sent)} communication(s) have been sent; the latest is '{latest.title}' via {latest.channel}."
    if surfaced:
        latest = surfaced[-1]
        return f"No communication has been sent yet. '{latest.title}' is drafted for {latest.audience} via {latest.channel}."
    return f"No communication draft is active. Customer tickets are {command.ticket_rate:.1f}× modelled baseline."


def _stress_text(session, command) -> str:
    if session.forecast:
        return (
            f"The current simulated projection says: {session.forecast.headline}. "
            f"The cascade model probability is {session.forecast.cascade_model_p:.0%}. "
            "Run the P2 stress analysis to compare a further shock; it does not execute a financial control."
        )
    return (
        f"A further-shock stress test is appropriate while risk is {command.risk_level}. "
        "It will remain modelled analysis only; any control requires human approval."
    )


def generate_reply(session, question: str) -> CopilotReply:
    """Compose a question-specific answer from fresh simulation evidence."""
    command = build_command(session)
    facts = _current_facts(session, command)
    intent = _intent(question)

    if not session.started:
        answer = "Start a simulated scenario first. Once it is running, I will generate a P2 briefing from the live modelled state, journal and execution evidence."
    elif intent == "change":
        delta = _window_delta(session, facts, _window_seconds(question))
        if delta:
            answer = f"Since {delta.since_label}: " + "; ".join(delta.lines) + "."
        else:
            answer = "There is not yet enough elapsed simulation history for a comparison. Current priority: " + command.first_priority + "."
    elif intent == "priority":
        answer = f"Start with {command.first_priority}. {command.why_first} Next: {command.next_step}"
    elif intent == "risk":
        alert_evidence = "; ".join(command.reasons)
        answer = (
            f"Risk is {command.risk_level} at {command.cascade_score:.0f}/100. {alert_evidence}. "
            f"Classifier context: {session.verdict.explanation}"
        )
    elif intent == "execution":
        answer = (
            f"Liquidation rate is {command.liquidation_rate:.1f}/min versus a {command.liquidation_baseline:.1f}/min baseline. "
            f"{_execution_evidence(command)}"
        )
    elif intent == "exposure":
        fund = facts["insurance_fund_pct"]
        answer = (
            f"Net modelled exposure is {command.exposure_pct:.1f}% of the configured limit; "
            f"{command.near_liquidation:,} positions are near modelled liquidation thresholds and the insurance fund is {fund:.1f}% of its start. "
            "Review exposure before proposing any control."
        )
    elif intent == "stress":
        answer = _stress_text(session, command)
    elif intent == "actions":
        answer = _queue_text(command) + f" Human approval remains required before any control or customer communication."
    elif intent == "team":
        team = "; ".join(f"{member.id} {member.status}: {member.responsibility}" for member in command.team)
        answer = f"Team state at {facts['sim_time']}: {team}."
    elif intent == "communications":
        answer = _communication_text(session, command)
    elif intent == "status":
        answer = (
            f"{facts['scenario']} is at {facts['sim_time']} in {facts['incident_state']} state. "
            f"There are {facts['decisions_recorded']} recorded decisions and {facts['communications_sent']} sent communications. "
            f"{command.first_priority} remains the P2 focus."
        )
    else:
        cluster = f" {command.abnormal_liquidations} execution(s) are flagged in {command.largest_cluster}." if command.largest_cluster else ""
        answer = (
            f"P2 briefing at {facts['sim_time']}. Risk is {command.risk_level} at {command.cascade_score:.0f}/100. "
            f"{'; '.join(command.reasons)}.{cluster} {command.first_priority}."
        )

    # A question is an explicit operator check-in. Save the exact underlying
    # fact state after composing so the next delta is simulation-derived.
    session.operator_snapshot = dict(facts)
    spoken = answer if len(answer) <= 520 else answer[:517].rsplit(" ", 1)[0] + "."
    return CopilotReply(
        answer=answer,
        spoken=spoken,
        first_priority=command.first_priority,
        why=command.reasons,
        next_step=command.next_step,
        facts=facts,
    )
