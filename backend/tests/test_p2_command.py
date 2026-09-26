"""P2 command state stays factual, auditable and exportable."""

from incident.copilot import generate_reply
from incident.report import build_pdf
from incident.session import IncidentSession


def _critical_session() -> IncidentSession:
    session = IncidentSession(time_fn=lambda: 0.0)
    session.start("C1", 8)
    session.clock.jump(900)
    session.advance()
    return session


def test_p2_command_exposes_live_cluster_and_audits_execution_decision():
    session = _critical_session()
    command = session.to_dto().command
    assert command is not None
    assert command.risk_level == "CRITICAL"
    assert command.cluster is not None
    assert len(command.cluster.executions) == 8

    execution = command.cluster.executions[0]
    session.decide_execution(execution.id, "investigate", "TL")
    refreshed = session.to_dto().command
    assert refreshed is not None and refreshed.cluster is not None
    assert refreshed.cluster.executions[0].status == "investigate"
    assert session.journal.entries[-1].actor == "TL"
    assert "modelled execution" in session.journal.entries[-1].action.lower()


def test_copilot_uses_structured_state_and_pdf_is_a_real_pdf():
    session = _critical_session()
    reply = generate_reply(session, "What should I do first?")
    assert reply.first_priority.startswith("Investigate liquidation cluster")
    assert reply.facts["liquidation_rate"] == session.to_dto().command.liquidation_rate

    delta = generate_reply(session, "What changed?")
    assert delta.answer
    pdf = build_pdf(session)
    assert pdf.startswith(b"%PDF-1.4")
