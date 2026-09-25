# H3: Playbooks, protective controls, communication templates

| | |
|---|---|
| Branch | `h3-playbooks` |
| Owner | B (teammate) |
| Size | M |
| Depends on | H0 |
| Blocks | H5 |

## Goal
Encode SPEC §5–7 (playbooks), §9.4 (controls), §10 (runbook phases/roles) and §11 (templates) as Python data plus small pure functions. H5 can then ask: "given this state, which actions and templates should be proposed right now, for which role, in what order, with what pre-filled text?"

This is mostly careful transcription from the spec, plus a small amount of logic. **No Python experience beyond dicts and functions is needed.**

## Read first
SPEC §4 (owners), §5, §6, §7, §9.4, §10, §11 · CONTRACTS §4 (`ControlDef`, `Effect`), §5 (`ActionView`, `TemplateView`) · H1's `scenarios/SCHEMA.md` for the `sim.*` effect knobs. If it isn't merged yet, use the knob names listed in H1 "Effects".

## You own
`backend/incident/content/__init__.py`, `content/controls.py`, `content/playbooks.py`, `content/templates.py`, `content/runbook.py`, `backend/tests/test_content.py`

## Design

**`controls.py`:** `CONTROLS: dict[str, ControlDef]` for all 10 rows of SPEC §9.4. Suggested effects (tune with A):

| id | effects | time_box_s |
|---|---|---|
| leverage_cap | `sim.max_leverage set 3` | — |
| reduce_only | `sim.new_exposure set 0`, `LIQ_RATE mult 0.6 ramp 120` | — |
| raise_mm | `sim.maintenance_mult set 1.3` | — |
| pause_liqs | `sim.liquidations_paused set 1` | 600 |
| fallback_feed | `ORACLE_DEV set 0.1 ramp 30`, `ORACLE_AGE set 1` | — |
| collateral_haircut | `STBL_PX` unchanged; `LIQ_RATE mult 0.7` (smoothed valuation) | — |
| pause_deposits | `SETTLE_FAIL_PCT mult 0.8` | — |
| ins_fund_topup | `sim.fund_topup_pct add 20` | — |
| load_shed | `ORDER_LATENCY_P95 mult 0.3 ramp 90`, `API_ERR_PCT mult 0.3 ramp 90` | — |
| freeze_hot_wallet | `WDR_QUEUE_RATIO add 20` (withdrawals stop) | — |

**`playbooks.py`:** `PLAYBOOKS: dict[Tag, Playbook]`, with one playbook per tag for all 18 tags. Each has `name`, `peak_sev`, `owner`, `triggers_text`, `steps: list[Step]`, `log_requirements`, `exit_text`. A `Step` has `id` (e.g. `"M2.2"`), `role`, `text`, optional `control_id`, optional `template_id`, `when` (a small predicate over the state, e.g. `lambda s: s.sev <= 2`; default always), and `rationale_hint` (a format string using live values, e.g. `"Insurance fund at {INS_FUND_PCT:.0f}%, falling {INS_FUND_TREND:.1f}%/min"`).

Function: `propose(state_view) -> list[ProposedAction]`. It takes active tags in `priority_order` (from H2, or copy the order from SPEC §8 into a constant), emits steps whose `when` is true and that haven't already been decided, assigns `priority`, and **caps visible proposals at 3 per role** (the rest get `queued=True`). Dedupe the same `control_id` across tags.

Also add the generic runbook actions from SPEC §10:
- "Acknowledge alert" (IC, target < 2 min).
- "Page founders" (IC, when SEV-1).
- "Customer update overdue" (CS, if > 15 sim-min since the last customer comm while SEV ≤ 2).
- "Review time-boxed control" (when `expires_t` passes).
- "Confirm step-down" (IC, when `pending` is set).

**`templates.py`:** `TEMPLATES: dict[str, TemplateDef]` for T1–T12 (text verbatim from SPEC §11) with `trigger(state) -> bool`:

| id | trigger |
|---|---|
| T1 | M1 active and state ≥ WARNING |
| T2 | SEV ≤ 2 |
| T3 | `reduce_only` approved |
| T4 | `pause_liqs` approved |
| T5 | S1 active |
| T6 | S4, S2 or R1 active |
| T7 | I2 or P3 active |
| T8 | any transition (internal) |
| T9 | S2, S3 or R1 active |
| T10 | SEV-1 (needs founder approval, noted in text) |
| T11 | I1 at ≥ WARNING |
| T12 | state RESOLVED |

`render(template_id, ctx) -> (text, missing[])` fills `{braces}` from a context dict built from live values: `asset`, `px_chg`, `window`, `instrument` (e.g. `NVDA-PERP`), `issue_summary`, `service`, `next_update_time`, `t_start`, `t_end`, `stablecoin`, `haircut_method`, `eta`, `official_channels`, `n`, `scenario_tags`, `one_line_state`, `role`, `action`, `link`, `metric`, `your_service`, `ic_name`, `phone`, `status_page_url`, `time`, `compensation_line_if_any`, `short_summary`. Unknown placeholders are left as `{name}` and listed in `missing`. Provide `DEFAULT_CTX` for the static ones (e.g. `official_channels="in-app and @MochaTrade on X"`).

T11 is special: build the top-3 FAQ answers from the active tags.

**`runbook.py`:** `phase_of(t) -> 'Detect'|'Escalate'|'Contain'|'Stabilise'|'Close'` and `ROLE_FOCUS[phase][role]` text (SPEC §10 table) for the UI's role header.

## Tasks
- [ ] 10 controls, 18 playbooks, 12 templates, runbook table.
- [ ] `propose()` and `render()` as above.
- [ ] Tests: every tag has a playbook; every step's `control_id`/`template_id` exists; every template renders with no `missing` given a full context built from `docs/contracts/fixtures/state_critical.json`; the per-role cap of 3 holds; SPEC §8 priority order holds (feed tags `[I1, M2, P3]` → the P3 steps come first).

## Acceptance criteria
- Tests green. `python -c "from incident.content.playbooks import PLAYBOOKS; print(len(PLAYBOOKS))"` → 18.
- A reviewer can diff each playbook against SPEC text and find no missing step.

## Out of scope
Deciding *when* actions become approved/done (H5), UI.
