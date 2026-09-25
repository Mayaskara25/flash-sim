"""Scenario tags (H2, SPEC §4 + §8 priority rule).

A signal at ≥ warn activates its catalogue tags — except the liquidation
signals (LIQ_RATE, LAR), which use the classifier verdict instead of their
own thresholds. Tags stay in the list forever; `active` reflects the current
tick. Flags activate security/rails tags that have no numeric signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from incident.catalogue import SIGNALS, status_of
from incident.contracts import SignalFrame, Tag, Verdict

LIQ_CODES = frozenset({"LIQ_RATE", "LAR"})

TAG_NAMES: dict[str, str] = {
    "M1": "Directional flash crash",
    "M2": "Liquidation cascade drains insurance fund",
    "M3": "Price gap → negative balances",
    "M4": "Mark-price oracle stale, wrong or manipulated",
    "M5": "Options volatility spike: short-gamma loss",
    "M6": "Concentrated (whale) position unwind",
    "S1": "Collateral stablecoin depeg",
    "S2": "Stablecoin chain congestion, issuer freeze or blacklist",
    "S3": "Hedge venue / liquidity provider outage or freeze",
    "S4": "Withdrawal run exceeds hot wallet + INR float",
    "S5": "INR ↔ USDT basis blowout",
    "P1": "Liquidation / risk engine bug",
    "P2": "Matching engine / API overload",
    "P3": "Hot wallet / key compromise",
    "R1": "UPI / banking partner freeze or throttle",
    "R2": "Regulatory action or access blocking",
    "I1": "Customer panic / information cascade",
    "I2": "Insolvency rumour / impersonation scams",
}

_BY_CODE = {s.code: s for s in SIGNALS}

#: SPEC §8 priority: security → funds integrity → solvency → availability →
#: communication → rest.
PRIORITY: list[str] = [
    "P3",
    "P1", "M4", "S1",
    "M2", "M3", "S3", "S4",
    "P2", "R1",
    "I1", "I2",
    "M1", "M5", "M6", "S2", "S5", "R2",
]
_PRIORITY_IDX = {tag: i for i, tag in enumerate(PRIORITY)}


def priority_order(tags: list[str]) -> list[str]:
    """Order tags per SPEC §8 (unknown tags go last, stable)."""
    return sorted(tags, key=lambda t: (_PRIORITY_IDX.get(t, 999), t))


def _hot(frame: SignalFrame, code: str) -> bool:
    v = frame.values.get(code)
    if v is None:
        return False
    return status_of(code, float(v)) in ("warn", "critical")


def active_triggers(frame: SignalFrame, verdict: Verdict) -> set[str]:
    """Tags whose trigger is present on this frame."""
    active: set[str] = set()
    for sig in SIGNALS:
        if sig.code in LIQ_CODES:
            continue
        v = frame.values.get(sig.code)
        if v is None:
            continue
        if status_of(sig.code, float(v)) in ("warn", "critical"):
            active.update(sig.tags)
    # Liquidation signals route through the classifier verdict.
    liq_hot = _hot(frame, "LIQ_RATE") or (
        frame.values.get("LAR") is not None
        and status_of("LAR", float(frame.values["LAR"])) in ("warn", "critical")
    )
    if liq_hot:
        if verdict == "MARKET":
            active.add("M1")
            try:
                fund = float(frame.values.get("INS_FUND_PCT", 100.0))
            except (TypeError, ValueError):
                fund = 100.0
            try:
                bad = float(frame.values.get("BAD_DEBT_RATE", 0.0))
            except (TypeError, ValueError):
                bad = 0.0
            if status_of("INS_FUND_PCT", fund) in ("warn", "critical") or bad > 0:
                active.add("M2")
        elif verdict == "SYSTEM":
            active.add("P1")
        elif verdict == "PRICING":
            active.add("M4")
        elif verdict == "COLLATERAL":
            active.add("S1")
        elif verdict == "INFORMATION":
            active.add("I1")
    else:
        # INFORMATION verdict without liquidation heat still tags I1 when
        # ticket/sentiment signals are hot (they already self-activate via
        # the catalogue loop above; this covers the verdict path).
        if verdict == "INFORMATION":
            active.add("I1")
    # Flags (no numeric signal): security / rails / attention.
    if frame.flags.get("wallet_compromise_suspected", False):
        active.add("P3")
    if frame.flags.get("regulatory_notice", False):
        active.add("R2")
    if frame.flags.get("cannot_close", False):
        active.add("P2")
    if frame.flags.get("stablecoin_frozen_address", False):
        active.add("S2")
    if frame.flags.get("media_attention", False):
        active.add("I2")
    if frame.flags.get("partner_notice", False):
        active.add("R1")
    return active


@dataclass
class TagInfo:
    tag: Tag
    name: str
    active: bool
    first_t: int
    peak_sev: int


@dataclass
class TagTracker:
    """Remembers every tag ever activated with first_t and peak SEV."""

    seen: dict[str, int] = field(default_factory=dict)  # tag -> first_t
    peaks: dict[str, int] = field(default_factory=dict)  # tag -> worst SEV (lower = worse)

    def update(
        self, t: int, frame: SignalFrame, verdict: Verdict, sev: int
    ) -> list[TagInfo]:
        active = active_triggers(frame, verdict)
        for tag in active:
            if tag not in self.seen:
                self.seen[tag] = t
                self.peaks[tag] = sev
            else:
                if sev < self.peaks[tag]:
                    self.peaks[tag] = sev
        # Tags that are merely seen but inactive keep their peak.
        out = [
            TagInfo(
                tag=tag,  # type: ignore[arg-type]
                name=TAG_NAMES.get(tag, tag),
                active=tag in active,
                first_t=self.seen[tag],
                peak_sev=self.peaks[tag],
            )
            for tag in self.seen
        ]
        out.sort(key=lambda i: _PRIORITY_IDX.get(i.tag, 999))
        return out
