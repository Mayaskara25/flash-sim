"""No-operator golden paths for the five additional compound scenarios."""

import pytest

from incident.scenario_loader import list_scenarios
from incident.session import IncidentSession


def session_for(scenario_id):
    wall = [0.]
    session = IncidentSession(lambda: wall[0])
    session.start(scenario_id, 8)
    session.forecaster = None  # Scenario rules are independent of H7 paths.
    return session, wall


def at(session, wall, minute):
    wall[0] = minute * 60 / 8
    dto = session.to_dto()
    while session.clock._consumed_t < minute * 60:
        dto = session.to_dto()
    return dto


def active(dto):
    return {tag.tag for tag in dto.tags if tag.active}


def drafts(dto):
    return {template.id for template in dto.templates if template.status == "surfaced"}


def test_scenario_catalogue():
    assert [row["id"] for row in list_scenarios()] == ["C1", "C2", "C3", "C4", "C5", "C6"]
    assert all(row["description"] for row in list_scenarios())


@pytest.mark.parametrize("scenario_id", ["C2", "C3", "C4", "C5", "C6"])
def test_preroll_has_no_incident_escalation(scenario_id):
    session, _ = session_for(scenario_id)
    assert session.machine.state in {"NORMAL", "WATCH"}
    assert not any(entry.sev <= 3 for entry in session.journal.entries)


def test_c2_depeg_wrong_way_chain():
    session, wall = session_for("C2")
    dto = at(session, wall, 3)
    assert dto.classifier.verdict == "COLLATERAL" and "S1" in active(dto)
    assert dto.severity.state != "EMERGENCY" and "t5" in drafts(dto)
    dto = at(session, wall, 12)
    assert "I2" in active(dto) and "t7" in drafts(dto)
    dto = at(session, wall, 14)
    assert dto.severity.state == "EMERGENCY"
    assert any("Stablecoin below" in reason for reason in dto.severity.overrides)
    dto = at(session, wall, 18)
    assert "S4" in active(dto) and "t6" in drafts(dto)


def test_c3_system_fault_and_wrongful_review():
    session, wall = session_for("C3")
    dto = at(session, wall, 3)
    assert dto.classifier.verdict == "SYSTEM"
    assert "P1" in active(dto) and "M1" not in active(dto)
    assert dto.severity.state == "EMERGENCY"
    assert any("Wrongful-liquidation risk" in reason for reason in dto.severity.overrides)
    pause = next(a for a in dto.actions if a.status == "proposed" and a.control_id == "pause_liqs")
    session.decide(pause.id, "approve", "IC", "Engine over-firing against a mild market move")
    assert session.controls["pause_liqs"].expires_t == dto.sim.t + 600
    session.review_liquidations("wrongful", "IC", "LAR 3.5 with a small price move")
    assert "t4" in drafts(session.to_dto())
    assert "compensation review" in " ".join(session.summary().open_items)


def test_c4_blocked_exit_and_rails():
    session, wall = session_for("C4")
    dto = at(session, wall, 5)
    assert "P2" in active(dto) and "t2" in drafts(dto)
    assert {"load_shed", "pause_liqs"}.issubset({a.control_id for a in dto.actions if a.status == "proposed"})
    dto = at(session, wall, 8)
    assert dto.severity.state == "EMERGENCY"
    assert any("unable to close" in reason for reason in dto.severity.overrides)
    dto = at(session, wall, 11)
    assert "R1" in active(dto) and {"t6", "t9"}.issubset(drafts(dto))


def test_c5_naked_book_stays_critical():
    session, wall = session_for("C5")
    dto = at(session, wall, 12)
    assert dto.severity.state == "CRITICAL"
    assert "S3" in active(dto) and "t9" in drafts(dto)
    assert any("backup hedge venue" in a.text for a in dto.actions if a.status == "proposed")


def test_c6_security_outweighs_market():
    session, wall = session_for("C6")
    dto = at(session, wall, 11)
    assert dto.severity.state == "EMERGENCY" and "P3" in active(dto)
    assert any("wallet/key compromise" in reason for reason in dto.severity.overrides)
    first = min((a for a in dto.actions if a.status == "proposed"), key=lambda a: a.priority)
    assert first.control_id == "freeze_hot_wallet" and "t7" in drafts(dto)


@pytest.mark.parametrize("event,tag,template", [
    ("stablecoin_dip", "S1", "t5"),
    ("api_overload", "P2", "t2"),
    ("rumour", "I2", "t7"),
])
def test_live_inject_surfaces_event(event, tag, template):
    session, wall = session_for("C1")
    session.injects.append((event, session.frame.t))
    dto = at(session, wall, .5)
    assert tag in active(dto) and template in drafts(dto)


def test_oracle_inject_surfaces_pause_notice_after_approval():
    session, wall = session_for("C1")
    session.injects.append(("oracle_stale", session.frame.t))
    dto = at(session, wall, .5)
    assert "M4" in active(dto)
    pause = next(a for a in dto.actions if a.status == "proposed" and a.control_id == "pause_liqs")
    session.decide(pause.id, "approve", "IC", "Verify the stale mark before further liquidations")
    assert "t4" in drafts(session.to_dto())


@pytest.mark.parametrize("scenario_id", ["C2", "C3", "C4", "C5", "C6"])
def test_scenario_replay_is_deterministic(scenario_id):
    def run():
        session, wall = session_for(scenario_id)
        dto = at(session, wall, 18)
        return (dto.severity.model_dump(), dto.classifier.model_dump(),
                [(tag.tag, tag.first_t) for tag in dto.tags],
                [entry.model_dump() for entry in dto.log])
    assert run() == run()
