"""H3 content and pure proposal contract checks."""

from incident.content.controls import CONTROLS
from incident.content.playbooks import PLAYBOOKS, ProposalContext, priority_order, propose
from incident.content.runbook import ROLE_FOCUS, phase_of
from incident.content.templates import TEMPLATES, render, triggered
from incident.contracts import Tag


ALL_TAGS: set[Tag] = {
    "M1", "M2", "M3", "M4", "M5", "M6", "S1", "S2", "S3", "S4", "S5",
    "P1", "P2", "P3", "R1", "R2", "I1", "I2",
}


def test_all_spec_content_is_present_and_references_resolve():
    assert len(CONTROLS) == 10
    assert len(TEMPLATES) == 12
    assert set(PLAYBOOKS) == ALL_TAGS
    assert all(c.effects for c in CONTROLS.values())
    ids = set()
    for tag, playbook in PLAYBOOKS.items():
        assert playbook.steps and playbook.triggers_text and playbook.log_requirements and playbook.exit_text
        for step in playbook.steps:
            assert step.id.startswith(f"{tag}.") and step.id not in ids
            ids.add(step.id)
            assert step.control_id is None or step.control_id in CONTROLS
            assert step.template_id is None or step.template_id in TEMPLATES


def test_priority_control_dedupe_and_role_cap():
    ctx = ProposalContext(active_tags=("I1", "M2", "P3"), sev=1, t=900)
    actions = propose(ctx)
    assert priority_order(list(ctx.active_tags)) == ["P3", "M2", "I1"]
    assert actions[0].tag == "P3"
    control_ids = [a.control_id for a in actions if a.control_id]
    assert len(control_ids) == len(set(control_ids))
    for role in ("IC", "TL", "CS"):
        visible = [a for a in actions if a.role == role and not a.queued]
        assert len(visible) <= 3
    assert any(a.queued for a in actions)


def test_decisions_and_active_controls_do_not_reappear():
    ctx = ProposalContext(active_tags=("M2",), sev=2, t=900,
                          decided_step_ids=frozenset({"M2.1"}),
                          active_controls=frozenset({"reduce_only"}))
    actions = propose(ctx)
    assert "M2.1" not in {a.id for a in actions}
    assert "reduce_only" not in {a.control_id for a in actions}


def test_template_render_with_full_context_and_unknown_placeholder():
    ctx = {
        "asset": "NVDA", "px_chg": 6, "window": 5, "instrument": "NVDA-PERP",
        "issue_summary": "a simulated market disruption", "service": "trading",
        "next_update_time": "T+20", "t_start": "T+0", "t_end": "T+10",
        "stablecoin": "USDT", "haircut_method": "a 30-minute average", "eta": "20 min",
        "n": 2, "scenario_tags": "M1, M2", "one_line_state": "Liquidations rising",
        "role": "IC", "action": "Check fund", "link": "incident console",
        "metric": "rejected orders", "your_service": "hedging", "ic_name": "IC",
        "phone": "on-file ops contact", "status_page_url": "official status page",
        "time": "T+55", "compensation_line_if_any": "Compensation review pending",
        "short_summary": "Signals normal", "tags": {"M1", "I1"},
    }
    for template_id in TEMPLATES:
        text, missing = render(template_id, ctx)
        assert text and not missing, (template_id, missing)
    text, missing = render("t3", {})
    assert "{instrument}" in text and missing == ["instrument"]


def test_trigger_and_runbook_boundaries():
    assert triggered("t3", tags={"M2"}, sev=2, state="CRITICAL", active_controls={"reduce_only"})
    assert not triggered("t3", tags={"M2"}, sev=2, state="CRITICAL")
    assert triggered("t12", tags=set(), sev=4, state="RESOLVED")
    assert [phase_of(t) for t in (0, 600, 1200, 2400, 3600)] == [
        "Detect", "Escalate", "Contain", "Stabilise", "Close"
    ]
    assert all(set(focus) >= {"IC", "TL", "CS"} for focus in ROLE_FOCUS.values())
