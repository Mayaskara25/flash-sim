"""Live, single-operator incident simulation and decision record."""

from __future__ import annotations

import json
from pathlib import Path
from time import monotonic
from typing import Callable

from .catalogue import SIGNALS, status_of
from .clock import SimClock
from .content.controls import CONTROLS
from .content.playbooks import ProposalContext, propose
from .content.templates import TEMPLATES, render, triggered
from .contracts import (ActionView, ActiveControl, AlertCard, ClassifierBlock,
                        Dims, IncidentStateDTO, PendingTransition, SeverityBlock,
                        SignalView, SimBlock, TagView, TemplateView, Thresholds)
from .log import IncidentLog, time_label
from .rules import (AlertManager, SignalHistory, StateMachine, TagTracker,
                    classify, score, sev_of_state)
from .scenario_loader import ScenarioLoader
from .signals import SignalGenerator
from .summary import build_summary

_IDLE = Path(__file__).resolve().parents[2] / "docs/contracts/fixtures/state_idle.json"


class SessionError(ValueError):
    def __init__(self, detail: str, status: int = 409):
        super().__init__(detail)
        self.status = status


class IncidentSession:
    def __init__(self, time_fn: Callable[[], float] | None = None) -> None:
        self.time_fn = time_fn
        self.reset()

    def reset(self) -> None:
        self.started = False
        self.scenario = None
        self.clock = SimClock(time_fn=self.time_fn, paused=True)
        self.generator = None
        self.history = SignalHistory()
        self.machine = StateMachine()
        self.tag_tracker = TagTracker()
        self.alert_manager = AlertManager()
        self.actions: dict[str, ActionView] = {}
        self.templates: dict[str, TemplateView] = {}
        self.controls: dict[str, ActiveControl] = {}
        self.journal = IncidentLog()
        self.frame = None
        self.verdict = None
        self.severity = None
        self.tags = []
        self.forecast = None
        from .forecast import compute
        self.forecaster = compute
        self.what_ifs = {}
        self.last_customer_comm_t = None
        self.peaks: dict[str, tuple[float, int]] = {}
        self.expired_controls: list[str] = []
        self.injects: list[tuple[str, int]] = []

    def start(self, scenario_id: str, speed: float = 8) -> IncidentStateDTO:
        try:
            scenario = ScenarioLoader.from_id(scenario_id)
            if speed <= 0:
                raise ValueError("speed must be positive")
        except (ValueError, FileNotFoundError) as exc:
            raise SessionError(str(exc), 422) from exc
        self.reset()
        self.started = True
        self.scenario = scenario
        self.generator = SignalGenerator(scenario)
        self.clock = SimClock(speed=speed, t0=-scenario.spec.preroll_s, time_fn=self.time_fn, paused=True)
        for t in range(-scenario.spec.preroll_s + 2, 1, 2):
            self._tick(t)
        self.clock.reset(0)
        self.clock.resume()
        return self.to_dto()

    def advance(self) -> None:
        if not self.started:
            return
        target = min(self.clock.now_t(), self.scenario.spec.duration_s)
        # A request processes at most 600 ticks. The next poll catches up.
        cursor = int(self.clock._consumed_t)
        last = min(target, cursor + 1200)
        for t in self.clock.ticks_until(last):
            self._tick(t)
        if target >= self.scenario.spec.duration_s and last >= target:
            self.clock.pause()

    def _snapshot(self) -> dict[str, float]:
        if self.frame is None:
            return {}
        ranked = sorted(SIGNALS, key=lambda sig: (status_of(sig.code, self.frame.values[sig.code]) == "normal", sig.code))
        return {s.code: round(self.frame.values[s.code], 3) for s in ranked[:6]}

    def _log(self, type: str, action: str, actor: str = "system", **kw) -> None:
        self.journal.append(t=self.frame.t if self.frame else 0, type=type,
                            sev=self._sev(), tags=[x.tag for x in self.tags if x.active],
                            actor=actor, action=action, snapshot=self._snapshot(), **kw)

    def _sev(self) -> int:
        return sev_of_state(self.machine.state, self.machine.pre_stabilising_sev)

    def _tick(self, t: int) -> None:
        for cid, c in list(self.controls.items()):
            if c.expires_t is not None and t >= c.expires_t:
                del self.controls[cid]
                self.expired_controls.append(cid)
                self._log("decision", f"{c.label} expired; review required", ref=cid)
        effects = [(effect, active.approved_t) for cid, active in self.controls.items()
                   for effect in CONTROLS[cid].effects]
        frame = self.generator.step(t, effects)
        # Injects are temporary test overlays; never rewrite scenario tracks.
        active_injects = [(event, start) for event, start in self.injects if t - start < 300]
        self.injects = active_injects
        if active_injects:
            from .contracts import SignalFrame
            values = dict(frame.values)
            flags = dict(frame.flags)
            for event, start in active_injects:
                strength = max(0.0, 1 - (t - start) / 300)
                if event == "stablecoin_dip":
                    values["STBL_PX"] = min(values["STBL_PX"], 1 - .018 * strength)
                elif event == "oracle_stale":
                    values["ORACLE_AGE"] = max(values["ORACLE_AGE"], 12 * strength)
                elif event == "api_overload":
                    values["API_ERR_PCT"] = max(values["API_ERR_PCT"], 4 * strength)
                    flags["cannot_close"] = strength > .5
                elif event == "rumour":
                    values["RUMOR_MENTIONS"] = max(values["RUMOR_MENTIONS"], 50 * strength)
                    flags["media_attention"] = strength > .5
            frame = SignalFrame(t=t, values=values, flags=flags, meta=frame.meta)
        self.frame = frame
        self.history.add(frame)
        self.verdict = classify(frame, self.history)
        self.severity = score(frame, self.history, self.verdict.verdict)
        _, transitions = self.machine.step(t, self.severity, frame)
        self.tags = self.tag_tracker.update(t, frame, self.verdict.verdict, self._sev())
        for event in transitions:
            self._log("transition", f"{event.from_state} → {event.to_state}")
        old_alerts = {(k, v.count) for k, v in self.alert_manager.cards.items()}
        self.alert_manager.update(t, frame)
        for card in self.alert_manager.cards.values():
            if (card.id, card.count) not in old_alerts:
                self._log("alert", f"{card.signal} {card.level} alert", ref=card.id)
        for sig in SIGNALS:
            value = frame.values[sig.code]
            current = self.peaks.get(sig.code)
            if current is None or (value > current[0] if sig.direction == "up" else value < current[0]):
                self.peaks[sig.code] = (value, t)
        self._refresh_proposals()
        self._refresh_templates(bool(transitions))
        if self.forecaster is not None and t >= 0 and t % 10 == 0:
            self.forecast, self.what_ifs = self.forecaster(self)

    def _refresh_proposals(self) -> None:
        ctx = ProposalContext(active_tags=tuple(x.tag for x in self.tags if x.active),
                              sev=self._sev(), t=self.frame.t, signals=self.frame.values,
                              decided_step_ids=frozenset(k for k, a in self.actions.items() if a.status != "proposed"),
                              active_controls=frozenset(self.controls),
                              pending_confirmation=self.machine.pending is not None,
                              last_customer_comm_t=self.last_customer_comm_t,
                              expired_controls=tuple(self.expired_controls),
                              unacknowledged_alerts=any(c.acknowledged_by is None for c in self.alert_manager.cards.values()))
        for row in propose(ctx):
            if row.id not in self.actions:
                self.actions[row.id] = ActionView(id=row.id, tag=row.tag, role=row.role,
                    text=row.text, priority=row.priority, control_id=row.control_id,
                    template_id=row.template_id, status="proposed", proposed_t=self.frame.t,
                    decided_t=None, decided_by=None, rationale=None,
                    rationale_hint=row.rationale_hint, expires_t=None, what_if=None)

    def _refresh_templates(self, transition: bool) -> None:
        tags = {x.tag for x in self.tags if x.active}
        context = dict(tags=tags, asset=self.scenario.spec.asset,
                       px_chg=round(self.frame.values.get("PX_CHG_5M", 0), 1), window=5,
                       instrument=self.scenario.spec.asset, service="trading", time=time_label(self.frame.t),
                       issue_summary="market volatility", next_update_time="15 minutes",
                       scenario_tags=", ".join(tags), n=self._sev(), one_line_state=self.machine.state,
                       role="IC", action="Review incident console", link="/", stablecoin="USDT",
                       haircut_method="the published collateral schedule", eta="being confirmed",
                       t_start=time_label(self.frame.t), t_end="pending review",
                       metric="degraded service", your_service="partner service",
                       short_summary="Conditions have stabilised", compensation_line_if_any="Any affected accounts are under review",
                       status_page_url="the status page")
        for tid, definition in TEMPLATES.items():
            if tid in self.templates or not triggered(tid, tags=tags, sev=self._sev(),
                                                      state=self.machine.state, active_controls=set(self.controls),
                                                      transition=transition):
                continue
            content, missing = render(tid, context)
            self.templates[tid] = TemplateView(id=tid, tag=next(iter(sorted(tags)), None),
                audience=definition.audience, channel=definition.channel, title=definition.title,
                text=content, missing=missing, status="surfaced", surfaced_t=self.frame.t,
                sent_t=None, approved_by=None)

    def to_dto(self) -> IncidentStateDTO:
        if not self.started:
            return IncidentStateDTO.model_validate(json.loads(_IDLE.read_text()))
        self.advance()
        pending = self.machine.pending
        signals = []
        active_tags = {x.tag for x in self.tags if x.active}
        for sig in SIGNALS:
            value = self.frame.values[sig.code]
            history = [(f.t, f.values[sig.code]) for f in self.history.frames_in(self.frame.t - 600, self.frame.t)]
            prior = self.history.value_at(sig.code, self.frame.t - 60)
            status = status_of(sig.code, value)
            signals.append(SignalView(code=sig.code, label=sig.label, unit=sig.unit,
                value=value, status=status, relevant=status != "normal" or bool(active_tags.intersection(sig.tags)),
                trend_per_min=value - prior if prior is not None else 0,
                history=history, thresholds=Thresholds(watch=sig.watch, warn=sig.warn, critical=sig.critical),
                direction=sig.direction))
        signals.sort(key=lambda s: (not s.relevant, {"critical": 0, "warn": 1, "watch": 2, "normal": 3}[s.status], s.code))
        for action in self.actions.values():
            action.what_if = self.what_ifs.get(action.control_id) if action.status == "proposed" else None
        reminders = []
        if pending:
            reminders.append(f"IC confirmation needed: {pending.kind}")
        if self.expired_controls:
            reminders.append("Review expired controls: " + ", ".join(self.expired_controls))
        if self.last_customer_comm_t is not None and self._sev() <= 2 and self.frame.t - self.last_customer_comm_t > 900:
            reminders.append("Customer update overdue")
        return IncidentStateDTO(
            sim=SimBlock(scenario_id=self.scenario.spec.id, scenario_name=self.scenario.spec.name,
                t=self.frame.t, t_label=time_label(self.frame.t), speed=self.clock.speed,
                running=not self.clock.paused, duration_s=self.scenario.spec.duration_s, started=True),
            severity=SeverityBlock(state=self.machine.state, sev=self._sev(), score=self.severity.score,
                dims=Dims(**self.severity.dims), overrides=self.severity.overrides,
                since_t=self.machine.since_t, pending=PendingTransition(kind=pending.kind,
                    **{"from": pending.from_state}, to=pending.to_state,
                    eligible_since_t=pending.eligible_since_t, needs="IC") if pending else None),
            classifier=ClassifierBlock(**vars(self.verdict)),
            tags=[TagView(**vars(tag)) for tag in self.tags], signals=signals,
            alerts=[AlertCard(id=c.id, signal=c.signal, level=c.level, count=c.count,
                              first_t=c.first_t, last_t=c.last_t, acknowledged_by=c.acknowledged_by)
                    for c in self.alert_manager.cards.values() if not c.superseded],
            actions=sorted(self.actions.values(), key=lambda a: (a.status != "proposed", a.priority, a.proposed_t)),
            templates=list(self.templates.values()), controls_active=list(self.controls.values()),
            log=self.journal.entries, forecast=self.forecast, reminders=reminders)

    def decide(self, action_id: str, decision: str, actor: str, rationale: str | None) -> None:
        action = self.actions.get(action_id)
        if action is None or action.status != "proposed":
            raise SessionError("Unknown or already decided action")
        if actor != action.role:
            raise SessionError(f"Action belongs to {action.role}")
        if decision in {"approve", "skip"} and not (rationale or "").strip():
            raise SessionError("rationale is required for approve/skip", 422)
        if decision == "done" and action.control_id:
            raise SessionError("Control actions require approval", 422)
        action.status = {"approve": "approved", "skip": "skipped", "done": "done"}[decision]
        action.decided_t = self.frame.t
        action.decided_by = actor
        action.rationale = rationale
        expires = None
        if decision == "approve" and action.control_id:
            control = CONTROLS[action.control_id]
            expires = self.frame.t + control.time_box_s if control.time_box_s else None
            self.controls[control.id] = ActiveControl(control_id=control.id, label=control.label,
                approved_t=self.frame.t, approved_by=actor, expires_t=expires, params=control.params)
            action.expires_t = expires
        self._log("decision", f"{decision}: {action.text}", actor, rationale=rationale,
                  approved_by=actor if decision == "approve" else None,
                  expires_at=expires, ref=action_id)
        self._refresh_templates(False)

    def send(self, template_id: str, actor: str, text: str) -> None:
        draft = self.templates.get(template_id)
        if draft is None or draft.status != "surfaced":
            raise SessionError("Unknown or already handled template")
        if not text.strip():
            raise SessionError("Message text is required", 422)
        draft.status, draft.sent_t, draft.approved_by = "sent", self.frame.t, actor
        draft.text = text
        if draft.audience == "Customer":
            self.last_customer_comm_t = self.frame.t
        self._log("comm", f"Sent {draft.title}: {text}", actor, ref=template_id)

    def dismiss(self, template_id: str, actor: str, rationale: str) -> None:
        draft = self.templates.get(template_id)
        if draft is None or draft.status != "surfaced":
            raise SessionError("Unknown or already handled template")
        if not rationale.strip():
            raise SessionError("Dismissal rationale is required", 422)
        draft.status = "dismissed"
        self._log("decision", f"Dismissed {draft.title}", actor, rationale=rationale, ref=template_id)

    def ack(self, alert_id: str, actor: str) -> None:
        try:
            card = self.alert_manager.ack(alert_id, actor)
        except ValueError as exc:
            raise SessionError(str(exc)) from exc
        self._log("decision", f"Acknowledged {card.signal} alert", actor, ref=alert_id)

    def confirm(self, actor: str) -> None:
        if not self.started:
            raise SessionError("Start a scenario first")
        try:
            events = self.machine.confirm(actor, self.frame.t)
        except ValueError as exc:
            raise SessionError(str(exc)) from exc
        for event in events:
            self._log("transition", f"{event.from_state} → {event.to_state}", actor)
        self._refresh_templates(bool(events))

    def manual_raise(self, sev: int, actor: str, reason: str) -> None:
        if not self.started:
            raise SessionError("Start a scenario first")
        if not reason.strip():
            raise SessionError("Reason is required", 422)
        events = self.machine.manual_raise(sev, self.frame.t)
        if not events:
            raise SessionError("Severity can only be raised")
        for event in events:
            self._log("transition", f"Manual raise: {event.from_state} → {event.to_state}", actor, rationale=reason)

    def review_liquidations(self, verdict: str, actor: str, rationale: str) -> None:
        if not self.started:
            raise SessionError("Start a scenario first")
        if not rationale.strip():
            raise SessionError("Review rationale is required", 422)
        self._log("decision", f"Liquidations: {verdict}", actor,
                  rationale=rationale, review=verdict)

    def summary(self):
        return build_summary(self)
