"""Scenario playbooks from SPEC §§5–8. Content only; H5 owns decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from incident.contracts import Role, Tag


@dataclass(frozen=True)
class ProposalContext:
    active_tags: tuple[Tag, ...]
    sev: int
    t: int
    signals: dict[str, float] = field(default_factory=dict)
    decided_step_ids: frozenset[str] = frozenset()
    active_controls: frozenset[str] = frozenset()
    pending_confirmation: bool = False
    last_customer_comm_t: int | None = None
    expired_controls: tuple[str, ...] = ()
    unacknowledged_alerts: bool = False


@dataclass(frozen=True)
class Step:
    id: str
    role: Role
    text: str
    control_id: str | None = None
    template_id: str | None = None
    rationale_hint: str = "Record the observed signal and reason for this decision."
    when: Callable[[ProposalContext], bool] | None = None


@dataclass(frozen=True)
class Playbook:
    tag: Tag
    name: str
    peak_sev: int
    owner: Role
    triggers_text: str
    steps: tuple[Step, ...]
    log_requirements: str
    exit_text: str


@dataclass(frozen=True)
class ProposedAction:
    id: str
    tag: Tag | None
    role: Role
    text: str
    priority: int
    control_id: str | None
    template_id: str | None
    rationale_hint: str
    queued: bool


def _book(tag: Tag, name: str, peak: int, owner: Role, trigger: str,
          rows: list[tuple[Role, str, str | None, str | None]],
          log: str, exit_text: str) -> Playbook:
    steps = tuple(Step(f"{tag}.{i}", role, text, control, template)
                  for i, (role, text, control, template) in enumerate(rows, 1))
    return Playbook(tag, name, peak, owner, trigger, steps, log, exit_text)


def _s(role: Role, text: str, control: str | None = None,
       template: str | None = None) -> tuple[Role, str, str | None, str | None]:
    return role, text, control, template


PLAYBOOKS: dict[Tag, Playbook] = {p.tag: p for p in [
    _book("M1", "Directional flash crash", 2, "IC", "PX_CHG_5M ≤ -5%; LIQ_RATE > 100/min with LAR 0.7–1.5", [
        _s("IC", "Acknowledge the crash alert."),
        _s("TL", "Confirm feed freshness and trading-engine health."),
        _s("IC", "Check LAR and record whether liquidations are market-driven."),
        _s("IC", "Consider capping leverage on new positions and raising initial margin.", "leverage_cap"),
        _s("CS", "Approve the factual volatility notice.", template="t1"),
        _s("IC", "Watch insurance fund and support-ticket rate for escalation."),
    ], "Cause classification and any leverage or margin change with reason.", "PX_CHG_5M > -2% and LIQ_RATE < 50/min for 10 min."),
    _book("M2", "Liquidation cascade drains insurance fund", 1, "IC", "INS_FUND_PCT < 60%, bad debt rising or ADL", [
        _s("IC", "Declare SEV-1 and page founders if the emergency override is active."),
        _s("IC", "Switch affected instruments to reduce-only.", "reduce_only"),
        _s("IC", "Consider partial liquidations or higher maintenance margin.", "raise_mm"),
        _s("IC", "Decide insurance-fund top-up amount and treasury source.", "ins_fund_topup"),
        _s("CS", "Prepare a factual ADL notice before ADL if unavoidable."),
        _s("TL", "Check that the liquidation engine is not over-firing."),
    ], "Reduce-only time, top-up amount/source, ADL decision and affected count.", "Fund stable 15 min, no bad debt, IC signs off on lifting reduce-only."),
    _book("M3", "Price gap beyond liquidation", 2, "IC", "Negative accounts after a gap past liquidation prices", [
        _s("IC", "Freeze negative accounts' withdrawals pending reconciliation."),
        _s("IC", "Choose and document negative-balance policy: absorb or pursue."),
        _s("IC", "Tighten leverage ahead of known gap-prone market opens.", "leverage_cap"),
    ], "Total negative balance and policy selected.", "All negative accounts reconciled and policy communicated."),
    _book("M4", "Bad or stale mark-price oracle", 1, "TL", "ORACLE_DEV > 0.5% or ORACLE_AGE > 5 s", [
        _s("TL", "Switch mark price to the fallback median feed.", "fallback_feed"),
        _s("IC", "Pause affected liquidations for at most 10 min and schedule review.", "pause_liqs"),
        _s("TL", "Snapshot liquidations since the first price deviation for review."),
        _s("CS", "Prepare notice that affected liquidations are under review.", template="t4"),
    ], "Feed switch, pause start/end and disputed liquidations.", "Deviation < 0.3% for 10 min; compensation review queued."),
    _book("M5", "Options short-gamma loss", 2, "IC", "IV spike and short-gamma loss, only if MochaTrade writes options", [
        _s("IC", "Widen option quotes."),
        _s("IC", "Move short-dated options to reduce-only.", "reduce_only"),
        _s("IC", "Order delta hedge on an external venue."),
    ], "Hedge trades and quote-width changes.", "Net Greeks return inside risk limits."),
    _book("M6", "Concentrated position unwind", 2, "IC", "TOP10_OI_SHARE > 25% with low margin ratio", [
        _s("IC", "Liquidate the large position in slices, not one market order."),
        _s("IC", "Hedge externally before the unwind."),
        _s("CS", "Ask the account owner to add margin."),
    ], "Slice schedule and slippage per slice.", "Position closed or margin restored."),
    _book("S1", "Collateral stablecoin depeg", 1, "IC", "STBL_PX < $0.985; below $0.97 for 5 min is SEV-1", [
        _s("IC", "Confirm depeg using independent reference venues."),
        _s("IC", "Apply the pre-chosen smoothed collateral haircut.", "collateral_haircut"),
        _s("IC", "Pause new deposits in the affected stablecoin.", "pause_deposits"),
        _s("IC", "Offer alternate-stablecoin conversion if liquidity exists."),
        _s("IC", "Rebalance treasury within pre-set limits."),
        _s("CS", "Approve the asset-specific customer notice.", template="t5"),
        _s("IC", "Contact issuer or custody partner if their flows are implicated."),
    ], "Independent sources, haircut method/time and treasury rebalances.", "STBL_PX ≥ $0.995 for 30 min."),
    _book("S2", "Chain congestion or issuer freeze", 2, "IC", "Settlement failures, slow confirmations or frozen address", [
        _s("TL", "Switch to an alternate supported network if available."),
        _s("IC", "Batch withdrawals while the chain is congested."),
        _s("CS", "Communicate withdrawal delays by network.", template="t6"),
    ], "Affected networks, queue size and switch decisions.", "Settlement baseline restored and queue cleared."),
    _book("S3", "Hedge venue or LP outage", 2, "IC", "LP rejects > 5% or net exposure breaches limit", [
        _s("TL", "Fail over to the backup hedge venue."),
        _s("IC", "Set affected instruments reduce-only until hedging recovers.", "reduce_only"),
        _s("IC", "Track unhedged exposure each minute."),
        _s("IC", "Request LP status through direct operations channel.", template="t9"),
    ], "Failover time and peak unhedged exposure.", "Exposure inside limit and hedge venue stable for 15 min."),
    _book("S4", "Withdrawal run", 1, "IC", "Withdrawal queue exceeds liquid treasury", [
        _s("IC", "Pull funds from cold storage and venues under the pre-signed plan."),
        _s("IC", "Process withdrawals in order without discretionary freezes."),
        _s("CS", "Publish a factual withdrawal wait estimate.", template="t6"),
        _s("CS", "Point to proof-of-reserves only if one exists."),
    ], "Treasury top-ups, queue depth and any withdrawal limits with reasons.", "Queue normal for 30 min."),
    _book("S5", "INR/USDT basis blowout", 3, "IC", "INR_BASIS_PCT > 1%", [
        _s("TL", "Re-quote conversion from a live reference source."),
        _s("IC", "Widen conversion spread temporarily."),
        _s("IC", "Temporarily cap per-user conversion size."),
    ], "Conversion rate changes and caps.", "Basis < 0.5% for 15 min."),
    _book("P1", "Liquidation or risk-engine bug", 1, "TL", "LAR > 2 with small market move or engine errors", [
        _s("TL", "Lead this as a platform incident."),
        _s("IC", "Pause liquidations for 10 min and reassess bad debt.", "pause_liqs"),
        _s("TL", "Preserve logs, timestamps and affected-account evidence."),
        _s("IC", "Choose reduce-only or full trading halt with rationale.", "reduce_only"),
        _s("CS", "Communicate only verified facts about the review.", template="t4"),
    ], "Pause rationale, evidence snapshot and affected accounts.", "Fix or rollback, normal LAR for 15 min, compensation review opened."),
    _book("P2", "Matching-engine or API overload", 1, "TL", "Latency > 1 s, errors > 2%, or users cannot close", [
        _s("TL", "Shed non-essential load first.", "load_shed"),
        _s("TL", "Prioritise close-position and add-margin requests."),
        _s("IC", "Pause liquidations for accounts with failed close or margin requests.", "pause_liqs"),
        _s("CS", "Publish degraded-performance status update.", template="t2"),
    ], "Degradation window and liquidations during it.", "Latency and errors below warning for 10 min."),
    _book("P3", "Hot-wallet or key compromise", 1, "TL", "Suspicious outflow, new withdrawal address or admin login", [
        _s("TL", "Freeze hot-wallet signing immediately.", "freeze_hot_wallet"),
        _s("TL", "Rotate affected keys and credentials."),
        _s("IC", "Contact custody partner and stablecoin issuer about freezes."),
        _s("TL", "Preserve security evidence and access logs."),
    ], "Freeze time, amounts and affected addresses.", "Keys rotated, loss quantified, founders and partners briefed."),
    _book("R1", "UPI or banking rail failure", 2, "IC", "UPI_FAIL_PCT > 5% or partner notice", [
        _s("TL", "Switch to contracted backup payment rail if available."),
        _s("CS", "Show deposit and withdrawal notice.", template="t6"),
        _s("IC", "Contact the payment partner through direct operations channel.", template="t9"),
        _s("IC", "Consider liquidation grace for users with failed margin deposits."),
    ], "Partner contact, rail switch and affected-user count.", "Payment success > 98% for 30 min."),
    _book("R2", "Regulatory action or access blocking", 1, "IC", "Regulator query, access block or partner exit", [
        _s("IC", "Escalate the notice to founders for ownership."),
        _s("CS", "Hold public communications to founder-approved statements."),
        _s("TL", "Preserve the complete incident record and notice."),
    ], "Notice received, people informed and approved statements.", "Founders confirm the response and next steps."),
    _book("I1", "Customer panic and information cascade", 3, "CS", "Ticket volume > 3× or negative sentiment", [
        _s("CS", "Confirm operational facts before messaging."),
        _s("CS", "Publish one clear update.", template="t1"),
        _s("CS", "Give Support the top-three canned FAQ.", template="t11"),
        _s("CS", "Pin answers to the top three repeated questions."),
        _s("IC", "Investigate faults revealed by tickets, especially withdrawals."),
    ], "Messages sent and top ticket themes.", "Ticket rate < 2× baseline."),
    _book("I2", "Insolvency rumour or impersonation", 2, "CS", "Rumour mentions rising or fake support accounts reported", [
        _s("CS", "Rebut rumours factually only when evidence is available."),
        _s("CS", "Warn users that MochaTrade never requests OTPs or transfers by DM.", template="t7"),
        _s("CS", "Report impersonator accounts to the platform."),
    ], "Rebuttals and impersonator reports.", "Rumour mentions decline for 30 min."),
]}


_PRIORITY = (
    "P3", "P1", "M4", "S1", "M2", "M3", "S3", "S4", "P2", "R1",
    "I1", "I2", "M1", "M5", "M6", "S2", "S5", "R2",
)


def priority_order(tags: tuple[Tag, ...] | list[Tag]) -> list[Tag]:
    return sorted(set(tags), key=lambda tag: _PRIORITY.index(tag))


def propose(ctx: ProposalContext) -> list[ProposedAction]:
    """Return ordered proposals; ``queued`` marks items beyond three per role.

    H5 must track terminal decisions by step id and activate controls itself.
    This function does not mutate session state or publish messages.
    """
    rows: list[tuple[Tag | None, Step]] = []
    # A suspected key compromise outranks routine incident administration.
    if "P3" in ctx.active_tags:
        rows.extend(("P3", step) for step in PLAYBOOKS["P3"].steps)
    if ctx.unacknowledged_alerts:
        rows.append((None, Step("runbook.ack", "IC", "Acknowledge the active incident alert.")))
    if ctx.sev == 1:
        rows.append((None, Step("runbook.founders", "IC", "Page founders for SEV-1.")))
    for tag in priority_order(ctx.active_tags):
        if tag == "P3":
            continue
        rows.extend((tag, step) for step in PLAYBOOKS[tag].steps)
    if ctx.sev <= 2 and ctx.last_customer_comm_t is not None and ctx.t - ctx.last_customer_comm_t > 900:
        rows.append((None, Step("runbook.update", "CS", "Send the overdue customer update.")))
    for control in ctx.expired_controls:
        rows.append((None, Step(f"runbook.review.{control}", "IC", f"Review expired {control} control.")))
    if ctx.pending_confirmation and "P3" not in ctx.active_tags:
        rows.insert(0, (None, Step("runbook.stepdown", "IC", "Confirm the pending severity step-down.")))
    elif ctx.pending_confirmation:
        rows.append((None, Step("runbook.stepdown", "IC", "Confirm the pending severity step-down.")))

    result: list[ProposedAction] = []
    seen_controls: set[str] = set(ctx.active_controls)
    counts: dict[Role, int] = {"IC": 0, "TL": 0, "CS": 0, "system": 0}
    for tag, step in rows:
        if step.id in ctx.decided_step_ids or (step.when and not step.when(ctx)):
            continue
        if step.control_id and step.control_id in seen_controls:
            continue
        if step.control_id:
            seen_controls.add(step.control_id)
        counts[step.role] += 1
        result.append(ProposedAction(step.id, tag, step.role, step.text, len(result) + 1,
                                     step.control_id, step.template_id, step.rationale_hint,
                                     counts[step.role] > 3))
    return result
