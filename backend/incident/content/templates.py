"""Human-approved message templates from SPEC §11.

``triggered`` only surfaces a draft. H5 must require a named approving actor
before it records a send; this module performs no external communication.
"""

from __future__ import annotations

from dataclasses import dataclass
from string import Formatter
from typing import Mapping

from incident.contracts import Tag


@dataclass(frozen=True)
class TemplateDef:
    id: str
    audience: str
    channel: str
    title: str
    trigger: str
    text: str


TEMPLATES: dict[str, TemplateDef] = {t.id: t for t in [
    TemplateDef("t1", "Customer", "in-app banner", "Volatility notice", "M1 at Warning", "Markets are moving sharply. {asset} is down {px_chg}% in the last {window} minutes. MochaTrade systems are operating normally. Leveraged positions carry higher liquidation risk right now; review your margin."),
    TemplateDef("t2", "Customer", "status page", "Status page update", "Any SEV-2+ confirmed", "We are investigating {issue_summary} affecting {service}. Your funds remain in your account. Next update by {next_update_time}."),
    TemplateDef("t3", "Customer", "in-app", "Reduce-only notice", "M2 reduce-only activated", "To protect all users during extreme volatility, {instrument} is in reduce-only mode: you can close or reduce positions but not open new ones. We will lift this once conditions stabilise."),
    TemplateDef("t4", "Customer", "in-app + email", "Liquidation pause notice", "M4 or P1 liquidation pause", "We have paused liquidations on {instrument} while we verify pricing. Liquidations between {t_start} and {t_end} are under review, and affected users will be contacted directly."),
    TemplateDef("t5", "Customer", "asset notice", "Stablecoin depeg notice", "S1 depeg", "{stablecoin} is trading below its usual $1 value on major markets. Deposits in {stablecoin} are paused. Collateral is valued using {haircut_method}. Other assets are unaffected."),
    TemplateDef("t6", "Customer", "withdrawal screen", "Withdrawal delay notice", "S4, S2 or R1", "Withdrawals are taking longer than usual (current estimate {eta}). Requests are processed in order; no action is needed from you."),
    TemplateDef("t7", "Customer", "security", "Security notice", "I2 or P3", "MochaTrade will never ask for your password, OTP, or a transfer through direct messages. Only trust updates on {official_channels}."),
    TemplateDef("t8", "Internal", "incident channel", "Internal escalation", "Any transition", "[SEV-{n}] {scenario_tags} — {one_line_state}. Owner: {role}. Needed now: {action}. Dashboard: {link}."),
    TemplateDef("t9", "Partner", "direct ops channel", "Partner status request", "S2, S3 or R1", "MochaTrade ops here. Since {t_start} we see {metric} on {your_service}. Please confirm status and ETA. Contact: {ic_name}, {phone}."),
    TemplateDef("t10", "Public", "official X account", "Public statement", "SEV-1; founder approval required", "We are aware of {issue_summary}. Our team is working on it. Updates at {status_page_url}."),
    TemplateDef("t11", "Support", "canned FAQ", "Top-3 FAQ", "I1 at Warning", "Top-3 answers auto-built from ticket themes: why was I liquidated, can I withdraw, is MochaTrade safe."),
    TemplateDef("t12", "Customer", "in-app", "Resolution notice", "Resolved", "The issue affecting {service} has been resolved as of {time}. {compensation_line_if_any}. Summary: {short_summary}."),
]}


# Defaults are statements the product can safely make without a live feed.
DEFAULT_CTX: dict[str, object] = {"official_channels": "in-app and the verified MochaTrade account"}


def triggered(template_id: str, *, tags: set[Tag], sev: int, state: str,
              active_controls: set[str] | frozenset[str] = frozenset(),
              transition: bool = False) -> bool:
    """Whether a draft should surface; false does not imply it was sent."""
    return {
        "t1": "M1" in tags and sev <= 3,
        "t2": sev <= 2,
        "t3": "reduce_only" in active_controls,
        "t4": "pause_liqs" in active_controls,
        "t5": "S1" in tags,
        "t6": bool(tags & {"S4", "S2", "R1"}),
        "t7": bool(tags & {"I2", "P3"}),
        "t8": transition,
        "t9": bool(tags & {"S2", "S3", "R1"}),
        "t10": sev == 1,
        "t11": "I1" in tags and sev <= 3,
        "t12": state == "RESOLVED",
    }[template_id]


def _faq(tags: set[Tag]) -> str:
    liq = "We are reviewing any abnormal liquidations; affected users will be contacted." if tags & {"P1", "M4"} else "Liquidations are being checked against the market move and your position margin."
    withdrawal = "Withdrawals are delayed; the in-app status shows the current estimate." if tags & {"S4", "R1", "S2"} else "Check the withdrawal screen for the latest status."
    safety = "We will publish confirmed operational updates through verified MochaTrade channels."
    return f"Why was I liquidated? {liq}\nCan I withdraw? {withdrawal}\nIs MochaTrade safe? {safety}"


def render(template_id: str, ctx: Mapping[str, object]) -> tuple[str, list[str]]:
    """Fill known placeholders; leave unknown names visible and report them."""
    if template_id not in TEMPLATES:
        raise KeyError(template_id)
    values = {**DEFAULT_CTX, **ctx}
    if template_id == "t11":
        return _faq(set(values.get("tags", ()))), []
    missing: list[str] = []
    parts: list[str] = []
    for literal, name, format_spec, conversion in Formatter().parse(TEMPLATES[template_id].text):
        parts.append(literal)
        if name is None:
            continue
        if name not in values or values[name] is None:
            missing.append(name)
            parts.append("{" + name + "}")
        else:
            value = values[name]
            if conversion == "r":
                value = repr(value)
            elif conversion == "s":
                value = str(value)
            parts.append(format(value, format_spec))
    return "".join(parts), missing
