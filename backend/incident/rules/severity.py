"""Severity score S + hard overrides (H2, SPEC §3).

`score(frame, history, verdict)` returns `SeverityResult(score, dims,
overrides)` with each dimension 0–5 and `S = 20 × (0.30F + 0.25B + 0.15A +
0.15V + 0.15R)` rounded to 1 dp. `overrides` are human-readable texts of the
active SEV-1 hard overrides (any one forces EMERGENCY in the state machine).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from incident.catalogue import SIGNALS, status_of
from incident.contracts import SignalFrame, Verdict

from .history import SignalHistory

DIM_WEIGHTS = {"F": 0.30, "B": 0.25, "A": 0.15, "V": 0.15, "R": 0.15}

# STBL_PX warn level: collateral-driven below this.
STBL_WARN = 0.985
# STBL_PX override level: SEV-1 when held 300 s.
STBL_OVERRIDE = 0.97
STBL_OVERRIDE_S = 300
CANNOT_CLOSE_OVERRIDE_S = 180


@dataclass(frozen=True)
class SeverityResult:
    score: float
    dims: dict[str, float]
    overrides: list[str] = field(default_factory=list)


def _status_score(status: str, warn_score: float = 3.0, crit_score: float = 5.0) -> float:
    if status == "critical":
        return crit_score
    if status == "warn":
        return warn_score
    if status == "watch":
        return 1.0
    return 0.0


def _get(frame: SignalFrame, code: str, default: float = 0.0) -> float:
    try:
        return float(frame.values.get(code, default))
    except (TypeError, ValueError):
        return default


def _dim_F(frame: SignalFrame, verdict: Verdict) -> float:
    parts = []
    # LAR counts only when liquidations are NOT market-explained.
    if verdict != "MARKET":
        parts.append(_status_score(status_of("LAR", _get(frame, "LAR", 1.0))))
    parts.append(_status_score(status_of("ORACLE_DEV", _get(frame, "ORACLE_DEV", 0.05))))
    parts.append(_status_score(status_of("STBL_PX", _get(frame, "STBL_PX", 1.0))))
    parts.append(
        _status_score(
            status_of("WDR_QUEUE_RATIO", _get(frame, "WDR_QUEUE_RATIO", 5.0)),
            warn_score=2.0,
            crit_score=4.0,
        )
    )
    parts.append(
        _status_score(
            status_of("NEG_BAL_ACCTS", _get(frame, "NEG_BAL_ACCTS", 0.0)),
            warn_score=2.0,
            # Negative balances already drive the balance-sheet dimension
            # through fund depletion. Keep the integrity warning visible
            # without counting that same loss twice as a SEV-1 score.
            crit_score=3.0,
        )
    )
    if frame.flags.get("wallet_compromise_suspected", False):
        parts.append(5.0)
    return max(parts) if parts else 0.0


def _dim_B(frame: SignalFrame) -> float:
    fund = _get(frame, "INS_FUND_PCT", 100.0)
    fund_part = 5.0 * min(max((100.0 - fund) / 50.0, 0.0), 1.0)
    parts = [fund_part]
    if _get(frame, "BAD_DEBT_RATE", 0.0) > 0.0:
        parts.append(2.0)
    parts.append(
        _status_score(status_of("NET_EXPOSURE_PCT", _get(frame, "NET_EXPOSURE_PCT", 20.0)))
    )
    return max(parts)


def _dim_A(frame: SignalFrame) -> float:
    parts = [
        _status_score(status_of("ORDER_LATENCY_P95", _get(frame, "ORDER_LATENCY_P95", 80.0))),
        _status_score(status_of("API_ERR_PCT", _get(frame, "API_ERR_PCT", 0.3))),
        _status_score(
            status_of("UPI_FAIL_PCT", _get(frame, "UPI_FAIL_PCT", 1.0)),
            warn_score=2.0,
            crit_score=4.0,
        ),
        _status_score(
            status_of("SETTLE_FAIL_PCT", _get(frame, "SETTLE_FAIL_PCT", 0.2)),
            warn_score=2.0,
            crit_score=4.0,
        ),
        _status_score(
            status_of("LP_REJECT_PCT", _get(frame, "LP_REJECT_PCT", 0.5)),
            warn_score=2.0,
            crit_score=4.0,
        ),
    ]
    if frame.flags.get("cannot_close", False):
        parts.append(5.0)
    return max(parts)


def _dim_V(frame: SignalFrame, history: SignalHistory) -> float:
    now_t = frame.t
    best_code: str | None = None
    best_stress = 0.0
    for sig in SIGNALS:
        v = frame.values.get(sig.code)
        if v is None:
            continue
        from .history import stress_of

        s = stress_of(sig.code, float(v))
        if s > best_stress:
            best_stress = s
            best_code = sig.code
    if best_code is None or best_stress < 0.2:
        return 0.0
    ago = history.stress_at(best_code, now_t - 300)
    ratio = best_stress / max(ago, 0.05)
    return min(max((ratio - 1.0) * 5.0, 0.0), 5.0)


def _dim_R(frame: SignalFrame) -> float:
    parts = [
        _status_score(
            status_of("TICKET_RATE", _get(frame, "TICKET_RATE", 1.0)),
            warn_score=1.0,
            crit_score=3.0,
        ),
        _status_score(
            status_of("SENTIMENT", _get(frame, "SENTIMENT", 0.1)),
            warn_score=2.0,
            crit_score=4.0,
        ),
        _status_score(
            status_of("RUMOR_MENTIONS", _get(frame, "RUMOR_MENTIONS", 0.0)),
            warn_score=2.0,
            crit_score=4.0,
        ),
    ]
    if frame.flags.get("media_attention", False):
        parts.append(3.0)
    if frame.flags.get("partner_notice", False):
        parts.append(3.0)
    if frame.flags.get("regulatory_notice", False):
        parts.append(5.0)
    return max(parts)


def _overrides(
    frame: SignalFrame, history: SignalHistory, verdict: Verdict
) -> list[str]:
    out: list[str] = []
    lar = _get(frame, "LAR", 1.0)
    # 1. Wrongful-liquidation risk: SYSTEM/PRICING verdict with LAR critical.
    if verdict in ("SYSTEM", "PRICING") and status_of("LAR", lar) == "critical":
        out.append(
            f"Wrongful-liquidation risk: LAR {lar:.1f} critical "
            f"({verdict.lower()}-driven cause)"
        )
    # 2. Insurance fund below 25%, or any ADL.
    fund = _get(frame, "INS_FUND_PCT", 100.0)
    if fund < 25.0:
        out.append(f"Insurance fund below 25% (at {fund:.1f}%)")
    if _get(frame, "ADL_COUNT", 0.0) > 0:
        out.append(
            f"Auto-deleveraging event (ADL_COUNT {_get(frame, 'ADL_COUNT', 0.0):.0f})"
        )
    # 3. Stablecoin below $0.97 for 5+ min.
    stbl = _get(frame, "STBL_PX", 1.0)
    if stbl < STBL_OVERRIDE and history.held(
        "STBL_PX", lambda v: v < STBL_OVERRIDE, STBL_OVERRIDE_S
    ):
        out.append(f"Stablecoin below $0.97 for 5+ min (at ${stbl:.4f})")
    # 4. Users unable to close / add margin for 3+ min.
    if frame.flags.get("cannot_close", False) and history.flag_held(
        "cannot_close", CANNOT_CLOSE_OVERRIDE_S
    ):
        out.append("Users unable to close positions or add margin for 3+ min")
    # 5. Suspected wallet / key compromise.
    if frame.flags.get("wallet_compromise_suspected", False):
        out.append("Suspected wallet/key compromise")
    return out


def score(
    frame: SignalFrame,
    history: SignalHistory,
    verdict: Verdict = "NONE",
) -> SeverityResult:
    dims = {
        "F": round(float(_dim_F(frame, verdict)), 2),
        "B": round(float(_dim_B(frame)), 2),
        "A": round(float(_dim_A(frame)), 2),
        "V": round(float(_dim_V(frame, history)), 2),
        "R": round(float(_dim_R(frame)), 2),
    }
    s = 20.0 * sum(DIM_WEIGHTS[k] * dims[k] for k in ("F", "B", "A", "V", "R"))
    return SeverityResult(
        score=round(s, 1),
        dims=dims,
        overrides=_overrides(frame, history, verdict),
    )
