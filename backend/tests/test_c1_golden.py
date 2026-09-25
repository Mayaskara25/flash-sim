"""Scripted C1 operator journey with a fake wall clock."""

from incident.session import IncidentSession


def at(session, wall, minutes):
    wall[0] = minutes * 60 / 8
    return session.to_dto()


def test_operator_run_resolves_without_emergency():
    wall = [0.0]
    session = IncidentSession(lambda: wall[0])
    session.start("C1", 8)
    states = []
    dto = at(session, wall, .5)
    for card in dto.alerts:
        session.ack(card.id, "IC")
    session.decide("M1.4", "approve", "IC", "Cap new leverage during sustained market stress")
    states.append(dto.severity.state)
    dto = at(session, wall, 6.5)
    for tid in ("t1", "t11"):
        session.send(tid, "CS", session.templates[tid].text)
    states.append(dto.severity.state)
    dto = at(session, wall, 14 + 40 / 60)
    assert dto.severity.state == "CRITICAL"
    session.decide("M2.2", "approve", "IC", "Reduce new exposure to protect the fund")
    session.send("t3", "CS", session.templates["t3"].text)
    session.send("t2", "CS", session.templates["t2"].text)
    session.review_liquidations("market-explained", "IC",
                                "Price fell sharply and LAR stayed near baseline")
    states.append(dto.severity.state)
    for minute in (18, 22, 28, 35, 40, 45, 50, 55, 58):
        dto = at(session, wall, minute)
        states.append(dto.severity.state)
        if dto.severity.pending:
            session.confirm("IC")
    assert "WARNING" in states and "CRITICAL" in states
    assert "EMERGENCY" not in states
    assert session.machine.state == "RESOLVED"
    summary = session.summary()
    assert len([x for x in summary.decisions if x.ref in ("M1.4", "M2.2")]) == 2
    assert len(summary.comms) >= 4
    assert summary.liquidation_reviews[0].liquidation_review == "market-explained"


def test_no_reduce_only_reaches_fund_override():
    wall = [0.0]
    session = IncidentSession(lambda: wall[0])
    session.start("C1", 8)
    at(session, wall, .5)
    session.decide("M1.4", "approve", "IC", "Cap new leverage")
    for minute in (15, 18, 20, 22, 25, 28):
        dto = at(session, wall, minute)
        if dto.severity.state == "EMERGENCY":
            assert 20 <= minute <= 28
            assert "Insurance fund below 25%" in " ".join(dto.severity.overrides)
            return
    raise AssertionError("Expected insurance-fund emergency")


def test_identical_runs_have_identical_journals():
    def replay():
        wall = [0.0]
        session = IncidentSession(lambda: wall[0])
        session.start("C1", 8)
        at(session, wall, 15)
        return [e.model_dump() for e in session.journal.entries]
    assert replay() == replay()


def test_live_priority_surfaces_reduce_only_at_critical():
    wall = [0.0]
    session = IncidentSession(lambda: wall[0])
    session.start("C1", 8)
    dto = at(session, wall, 14 + 40 / 60)
    visible_ic = sorted((a for a in dto.actions if a.status == "proposed" and a.role == "IC"),
                        key=lambda a: a.priority)[:3]
    assert "M2.2" in [a.id for a in visible_ic]
