"""Real session transport and validation, replacing H0 click-through checks."""

import pytest
from fastapi.testclient import TestClient

from incident.contracts import IncidentStateDTO, IncidentSummary
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    client.post("/incident/reset")


def post(path, payload=None, expected=200):
    res = client.post("/incident" + path, json=payload)
    assert res.status_code == expected, res.text
    if expected == 200:
        return IncidentStateDTO.model_validate(res.json())
    return res.json()["detail"]


def test_catalogue_and_scenarios():
    assert len(client.get("/incident/catalogue").json()["controls"]) == 10
    assert [s["id"] for s in client.get("/incident/scenarios").json()] == ["C1"]


def test_idle_start_and_reset():
    assert client.get("/incident/state").json()["sim"]["started"] is False
    assert post("/start", {"scenario_id": "C1", "speed": 8}).sim.started
    assert post("/reset").sim.started is False


def test_api_actions_and_errors():
    assert "Start" in post("/notes", {"actor": "IC", "text": "x"}, 409)
    post("/start", {"scenario_id": "C1", "speed": 8})
    state = post("/clock", {"op": "jump", "t": 900})
    assert state.sim.t >= 900
    assert state.actions
    action = next(a for a in state.actions if a.id == "M2.2")
    assert "rationale" in post(f"/actions/{action.id}/decide", {"decision": "approve", "actor": "IC"}, 422)
    state = post(f"/actions/{action.id}/decide", {"decision": "approve", "actor": "IC", "rationale": "Capped new leverage"})
    assert any(c.control_id == "reduce_only" for c in state.controls_active)
    assert "already decided" in post(f"/actions/{action.id}/decide", {"decision": "approve", "actor": "IC", "rationale": "again"}, 409)
    state = post("/notes", {"actor": "TL", "text": "Engine verified"})
    assert state.log[-1].type == "note"
    state = post("/liquidations/review", {"verdict": "market-explained", "actor": "IC", "rationale": "LAR near one"})
    assert state.log[-1].liquidation_review == "market-explained"
    assert "No pending" in post("/pending/confirm", {"actor": "IC"}, 409)
    assert "only be raised" in post("/severity", {"sev": 4, "actor": "IC", "reason": "test"}, 409)
    assert IncidentSummary.model_validate(client.get("/incident/summary").json()).scenario_id == "C1"


def test_templates_alerts_and_inject():
    post("/start", {"scenario_id": "C1"})
    state = post("/clock", {"op": "jump", "t": 390})
    assert state.alerts
    state = post(f"/alerts/{state.alerts[0].id}/ack", {"actor": "IC"})
    assert state.alerts[0].acknowledged_by == "IC"
    draft = next(t for t in state.templates if t.id == "t1")
    state = post(f"/templates/{draft.id}/send", {"actor": "CS", "text": draft.text})
    assert next(t for t in state.templates if t.id == "t1").status == "sent"
    assert post("/inject", {"event": "stablecoin_dip"}).sim.started

