"""Synchronized incident session HTTP API (CONTRACTS §7)."""

from __future__ import annotations

from threading import RLock

from fastapi import APIRouter, HTTPException

from .catalogue import SIGNALS
from .content.controls import CONTROLS
from .content.templates import TEMPLATES
from .contracts import (ActionDecideBody, AlertAckBody, CatalogueDTO, ClockBody,
                        IncidentStateDTO, IncidentSummary, InjectBody,
                        LiquidationReviewBody, NotesBody, PendingConfirmBody,
                        ScenarioSummary, SeverityBody, StartBody,
                        TemplateCatalogueEntry, TemplateDismissBody, TemplateSendBody)
from .session import IncidentSession, SessionError

router = APIRouter()
_lock = RLock()
_session = IncidentSession()


def _run(operation):
    with _lock:
        try:
            _session.advance()
            operation()
            return _session.to_dto()
        except SessionError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@router.get("/scenarios", response_model=list[ScenarioSummary])
def scenarios():
    from .scenario_loader import list_scenarios
    expected = {"C1": ["M1", "I1", "M2"], "C2": ["S1", "I2", "S4"],
                "C3": ["M1", "P1"], "C4": ["M1", "P2", "R1"],
                "C5": ["M1", "S3", "M5"], "C6": ["M1", "I1", "P3"]}
    return [ScenarioSummary(**item, tags_expected=expected.get(item["id"], []))
            for item in list_scenarios()]


@router.get("/catalogue", response_model=CatalogueDTO)
def catalogue():
    return CatalogueDTO(signals=SIGNALS, controls=list(CONTROLS.values()),
        templates=[TemplateCatalogueEntry(id=t.id, audience=t.audience, channel=t.channel,
                                          title=t.title, trigger=t.trigger) for t in TEMPLATES.values()])


@router.post("/start", response_model=IncidentStateDTO)
def start(body: StartBody):
    return _run(lambda: _session.start(body.scenario_id, body.speed))


@router.post("/reset", response_model=IncidentStateDTO)
def reset():
    return _run(_session.reset)


@router.get("/state", response_model=IncidentStateDTO)
def state():
    return _run(lambda: None)


@router.post("/clock", response_model=IncidentStateDTO)
def clock(body: ClockBody):
    def change():
        try:
            if not _session.started:
                raise SessionError("Start a scenario first")
            if body.op == "pause":
                _session.clock.pause()
            elif body.op == "resume":
                _session.clock.resume()
            elif body.op == "speed":
                if body.speed is None:
                    raise SessionError("speed is required", 422)
                _session.clock.set_speed(body.speed)
            elif body.op == "jump":
                if body.t is None:
                    raise SessionError("t is required", 422)
                if body.t < _session.clock.now_t() or body.t > _session.scenario.spec.duration_s:
                    raise SessionError("jump target must be ahead and inside scenario", 422)
                _session.clock.jump(body.t)
                while _session.clock._consumed_t < body.t:
                    _session.advance()
        except ValueError as exc:
            raise SessionError(str(exc), 422) from exc
    return _run(change)


@router.post("/alerts/{alert_id}/ack", response_model=IncidentStateDTO)
def ack_alert(alert_id: str, body: AlertAckBody):
    return _run(lambda: _session.ack(alert_id, body.actor))


@router.post("/actions/{action_id}/decide", response_model=IncidentStateDTO)
def decide_action(action_id: str, body: ActionDecideBody):
    return _run(lambda: _session.decide(action_id, body.decision, body.actor, body.rationale))


@router.post("/templates/{template_id}/send", response_model=IncidentStateDTO)
def send_template(template_id: str, body: TemplateSendBody):
    return _run(lambda: _session.send(template_id, body.actor, body.text))


@router.post("/templates/{template_id}/dismiss", response_model=IncidentStateDTO)
def dismiss_template(template_id: str, body: TemplateDismissBody):
    return _run(lambda: _session.dismiss(template_id, body.actor, body.rationale))


@router.post("/notes", response_model=IncidentStateDTO)
def note(body: NotesBody):
    def add():
        if not _session.started:
            raise SessionError("Start a scenario first")
        if not body.text.strip():
            raise SessionError("Note text is required", 422)
        _session._log("note", body.text, body.actor)
    return _run(add)


@router.post("/severity", response_model=IncidentStateDTO)
def severity(body: SeverityBody):
    return _run(lambda: _session.manual_raise(body.sev, body.actor, body.reason))


@router.post("/pending/confirm", response_model=IncidentStateDTO)
def confirm(body: PendingConfirmBody):
    return _run(lambda: _session.confirm(body.actor))


@router.post("/liquidations/review", response_model=IncidentStateDTO)
def review(body: LiquidationReviewBody):
    return _run(lambda: _session.review_liquidations(body.verdict, body.actor, body.rationale))


@router.post("/inject", response_model=IncidentStateDTO)
def inject(body: InjectBody):
    def add():
        if not _session.started:
            raise SessionError("Start a scenario first")
        _session.injects.append((body.event, _session.frame.t))
        _session._log("note", f"Injected {body.event} overlay for five sim-minutes")
    return _run(add)


@router.get("/summary", response_model=IncidentSummary)
def summary():
    with _lock:
        _session.advance()
        return _session.summary()
