"""Every endpoint in CONTRACTS.md §7 responds and validates (H0 stub —
`backend/incident/api.py`). Also checks the pre-existing `/overview` route
(and a couple of siblings) still work once the incident router is mounted.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from incident.contracts import IncidentStateDTO, IncidentSummary
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_incident_session():
    """Stub session is a module-level singleton; reset before every test so
    tests don't depend on execution order (advisor guidance: design for
    isolation up front rather than retrofit it)."""
    client.post("/incident/reset")
    yield


def test_existing_overview_route_still_works():
    res = client.get("/overview")
    assert res.status_code == 200
    assert "simulated" in res.json()


def test_health_route_still_works():
    res = client.get("/health")
    assert res.status_code == 200


def test_get_state_returns_idle_before_start():
    res = client.get("/incident/state")
    assert res.status_code == 200
    dto = IncidentStateDTO.model_validate(res.json())
    assert dto.sim.started is False


def test_start_moves_to_normal():
    res = client.post("/incident/start", json={"scenario_id": "C1", "speed": 8})
    assert res.status_code == 200
    dto = IncidentStateDTO.model_validate(res.json())
    assert dto.sim.started is True
    assert dto.severity.state == "NORMAL"


def test_reset_returns_to_idle():
    client.post("/incident/start", json={"scenario_id": "C1"})
    res = client.post("/incident/reset")
    assert res.status_code == 200
    dto = IncidentStateDTO.model_validate(res.json())
    assert dto.sim.started is False


def test_get_scenarios():
    res = client.get("/incident/scenarios")
    assert res.status_code == 200
    body = res.json()
    assert {s["id"] for s in body} == {"C1", "C2", "C3", "C4", "C5", "C6"}


def test_get_catalogue():
    res = client.get("/incident/catalogue")
    assert res.status_code == 200
    body = res.json()
    assert len(body["signals"]) == 21
    assert len(body["controls"]) == 10
    assert len(body["templates"]) == 12


def test_clock_advances_state():
    client.post("/incident/start", json={"scenario_id": "C1"})
    res = client.post("/incident/clock", json={"op": "resume"})
    assert res.status_code == 200
    dto = IncidentStateDTO.model_validate(res.json())
    assert dto.severity.state == "WARNING"


def test_alert_ack_advances_and_returns_valid_state():
    client.post("/incident/start", json={"scenario_id": "C1"})
    res = client.post("/incident/alerts/al-liq-warn/ack", json={"actor": "IC"})
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_action_decide_requires_rationale_for_approve():
    res = client.post(
        "/incident/actions/a4/decide",
        json={"decision": "approve", "actor": "IC", "rationale": None},
    )
    assert res.status_code == 422
    assert "detail" in res.json()


def test_action_decide_with_rationale_ok():
    res = client.post(
        "/incident/actions/a4/decide",
        json={"decision": "approve", "actor": "IC", "rationale": "Fund draining fast."},
    )
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_action_decide_done_without_rationale_ok():
    res = client.post(
        "/incident/actions/a4/decide",
        json={"decision": "done", "actor": "IC"},
    )
    assert res.status_code == 200


def test_template_send():
    res = client.post("/incident/templates/t1/send", json={"actor": "CS", "text": "Edited notice text"})
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_template_dismiss():
    res = client.post("/incident/templates/t1/dismiss", json={"actor": "CS", "rationale": "Not needed"})
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_notes():
    res = client.post("/incident/notes", json={"actor": "IC", "text": "Watching LAR closely."})
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_severity_manual_raise():
    res = client.post("/incident/severity", json={"sev": 2, "actor": "IC", "reason": "Manual escalation"})
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_pending_confirm():
    res = client.post("/incident/pending/confirm", json={"actor": "IC"})
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_liquidations_review():
    res = client.post(
        "/incident/liquidations/review",
        json={"verdict": "market-explained", "actor": "IC", "rationale": "LAR nominal"},
    )
    assert res.status_code == 200
    IncidentStateDTO.model_validate(res.json())


def test_inject_jumps_to_emergency_variant():
    client.post("/incident/start", json={"scenario_id": "C1"})
    res = client.post("/incident/inject", json={"event": "stablecoin_dip"})
    assert res.status_code == 200
    dto = IncidentStateDTO.model_validate(res.json())
    assert dto.severity.state == "EMERGENCY"


def test_get_summary():
    res = client.get("/incident/summary")
    assert res.status_code == 200
    summary = IncidentSummary.model_validate(res.json())
    assert summary.scenario_id == "C1"


def test_clicking_through_the_full_sequence_stays_valid():
    client.post("/incident/start", json={"scenario_id": "C1"})
    seen_states = []
    for _ in range(8):
        res = client.post("/incident/notes", json={"actor": "IC", "text": "advance"})
        dto = IncidentStateDTO.model_validate(res.json())
        seen_states.append(dto.severity.state)
    assert seen_states[-1] == "RESOLVED"
