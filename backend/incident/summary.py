"""Incident report assembled from recorded events and observed signal peaks."""

from .contracts import IncidentSummary, PeakEntry


def build_summary(session) -> IncidentSummary:
    entries = session.journal.entries
    decisions = [e for e in entries if e.type == "decision"]
    comms = [e for e in entries if e.type == "comm"]
    reviews = [e for e in entries if e.liquidation_review is not None]
    timeline = [e for e in entries if e.type == "transition"]
    open_items: list[str] = []
    if session.started and not reviews and any(t.tag in {"M1", "M2", "P1", "M4"} for t in session.tags):
        open_items.append("Review liquidations against market and engine evidence.")
    for control in session.controls.values():
        if control.expires_t is not None:
            open_items.append(f"Review active {control.label} before expiry.")
    if any(e.liquidation_review == "wrongful" for e in reviews):
        open_items.append("Complete compensation review for wrongful liquidations.")
    peaks = [PeakEntry(signal=code, value=value, t=t) for code, (value, t) in session.peaks.items()]
    peak_sev = min((e.sev for e in entries), default=4)
    lines = [f"# {session.scenario.spec.name if session.started else 'Incident'} summary",
             f"Peak severity: SEV-{peak_sev}", "", "## Timeline"]
    lines += [f"- {e.t_label}: {e.action}" for e in timeline] or ["- No transitions recorded."]
    lines += ["", "## Decisions"] + ([f"- {e.t_label}: {e.action} — {e.rationale or 'No rationale'}" for e in decisions] or ["- None."])
    lines += ["", "## Communications"] + ([f"- {e.t_label}: {e.action}" for e in comms] or ["- None."])
    lines += ["", "## Open items"] + ([f"- {x}" for x in open_items] or ["- None."])
    return IncidentSummary(scenario_id=session.scenario.spec.id if session.started else "",
                           started_t=0, ended_t=session.clock.now_t() if session.machine.state == "RESOLVED" else None,
                           peak_sev=peak_sev, timeline=timeline, peaks=peaks,
                           decisions=decisions, comms=comms, liquidation_reviews=reviews,
                           open_items=open_items, markdown="\n".join(lines))
