"""Market-vs-system classifier (H2, SPEC §9.2).

Precedence (H2 handoff):
  COLLATERAL (LAR high + STBL_PX < 0.985)
  → PRICING (LAR high + ORACLE_DEV ≥ warn)
  → SYSTEM (LAR > 2.0 + small price move)
  → MARKET (LAR 0.7–1.5 + large down move, or LIQ_RATE ≥ watch)
  → INFORMATION (tickets/sentiment ≥ warn, nothing else ≥ warn)
  → NONE
"""

from __future__ import annotations

from dataclasses import dataclass

from incident.catalogue import status_of
from incident.contracts import SignalFrame, Verdict

from .history import SignalHistory

#: Signals that count as "information" for the INFORMATION verdict. Any other
#: signal at ≥ warn blocks INFORMATION.
INFO_CODES = frozenset({"TICKET_RATE", "SENTIMENT", "RUMOR_MENTIONS"})

#: LAR ≥ warn counts as "high" for COLLATERAL / PRICING.
LAR_HIGH = 2.0


@dataclass(frozen=True)
class ClassifierResult:
    verdict: Verdict
    lar: float
    l_obs: float
    l_exp: float
    explanation: str


def _num(frame: SignalFrame, code: str, default: float) -> float:
    v = frame.values.get(code, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def classify(frame: SignalFrame, history: SignalHistory | None = None) -> ClassifierResult:
    _ = history  # reserved: smoothed LAR / trend checks live here later.
    lar = _num(frame, "LAR", 1.0)
    l_obs = float(frame.meta.get("L_obs", frame.values.get("LIQ_RATE", 0.0)))
    l_exp = float(frame.meta.get("L_exp", 0.0))
    if not l_exp and lar:
        l_exp = l_obs / lar if lar else 0.0

    px = _num(frame, "PX_CHG_5M", 0.0)
    liq = _num(frame, "LIQ_RATE", 0.0)
    stbl = _num(frame, "STBL_PX", 1.0)
    oracle_dev = _num(frame, "ORACLE_DEV", 0.0)
    tickets = _num(frame, "TICKET_RATE", 1.0)
    sentiment = _num(frame, "SENTIMENT", 0.1)

    lar_high = lar >= LAR_HIGH
    stbl_bad = stbl < 0.985  # warn threshold for STBL_PX
    oracle_bad = status_of("ORACLE_DEV", oracle_dev) in ("warn", "critical")
    small_move = abs(px) < 3.0
    market_lar = 0.7 <= lar <= 1.5
    big_down = px <= -2.0
    liq_active = status_of("LIQ_RATE", liq) in ("watch", "warn", "critical")
    info_hot = status_of("TICKET_RATE", tickets) in ("warn", "critical") or status_of(
        "SENTIMENT", sentiment
    ) in ("warn", "critical")

    if lar_high and stbl_bad:
        return ClassifierResult(
            verdict="COLLATERAL",
            lar=lar,
            l_obs=l_obs,
            l_exp=l_exp,
            explanation=(
                f"LAR {lar:.1f} with stablecoin at ${stbl:.4f}: liquidations "
                "are collateral-driven (depeg shrinking margin)."
            ),
        )
    if lar_high and oracle_bad:
        return ClassifierResult(
            verdict="PRICING",
            lar=lar,
            l_obs=l_obs,
            l_exp=l_exp,
            explanation=(
                f"LAR {lar:.1f} with oracle deviation {oracle_dev:.2f}%: "
                "liquidations are pricing-driven (bad marks)."
            ),
        )
    if lar > 2.0 and small_move:
        return ClassifierResult(
            verdict="SYSTEM",
            lar=lar,
            l_obs=l_obs,
            l_exp=l_exp,
            explanation=(
                f"LAR {lar:.1f} on a {px:+.1f}% move: liquidations are "
                "system-driven (engine over-firing)."
            ),
        )
    if (market_lar and big_down) or liq_active:
        return ClassifierResult(
            verdict="MARKET",
            lar=lar,
            l_obs=l_obs,
            l_exp=l_exp,
            explanation=(
                f"LAR {lar:.1f} with price {px:+.1f}%/5m and "
                f"{liq:.0f}/min liquidations: market-driven."
            ),
        )
    if info_hot:
        others_hot = any(
            status_of(code, _num(frame, code, 0.0)) in ("warn", "critical")
            for code in frame.values
            if code not in INFO_CODES and code != "PX"
        )
        if not others_hot:
            return ClassifierResult(
                verdict="INFORMATION",
                lar=lar,
                l_obs=l_obs,
                l_exp=l_exp,
                explanation=(
                    f"Tickets {tickets:.1f}x and sentiment {sentiment:+.2f} "
                    "with systems normal: information-driven panic."
                ),
            )
    return ClassifierResult(
        verdict="NONE",
        lar=lar,
        l_obs=l_obs,
        l_exp=l_exp,
        explanation=(
            f"LAR {lar:.1f}, price {px:+.1f}%/5m: no clear market or "
            "system cause."
        ),
    )
