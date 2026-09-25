"""The signal catalogue (CONTRACTS §2 / SPEC §9.1), as code.

`SIGNALS` is the backend constant table served (wrapped in `CatalogueDTO`)
at `GET /incident/catalogue`. `status_of` is the shared threshold rule used
by H1 (signal generation) and H2 (rules engine) so both read status off the
same table instead of re-implementing the comparison.

Threshold rule (H0 handoff): for `direction == 'up'`, a signal is at a given
level once `value >= threshold`; for `direction == 'down'`, once
`value <= threshold`. A `None` threshold for a level is skipped (that level
never matches). The returned status is the *highest* matching level among
watch/warn/critical, else `'normal'`.
"""

from __future__ import annotations

from .contracts import SignalDef, SignalStatus

# CONTRACTS §2. `NET_EXPOSURE_USD` from SPEC is expressed here as
# `NET_EXPOSURE_PCT` of the risk limit. `RUMOR_MENTIONS` is added for I2.
# `PX` (underlying price level, USD) is emitted in SignalFrame.values for
# the price chart but has no thresholds, so it is not part of this catalogue.
SIGNALS: list[SignalDef] = [
    SignalDef(
        code="PX_CHG_5M", label="Underlying price change (5m)", unit="%",
        baseline=0, watch=-2, warn=-5, critical=-10, direction="down",
        tags=["M1", "M3"],
    ),
    SignalDef(
        code="LIQ_RATE", label="Liquidation rate", unit="/min",
        baseline=5, watch=30, warn=100, critical=300, direction="up",
        tags=["M1", "M2"],
    ),
    SignalDef(
        code="LAR", label="Liquidation anomaly ratio", unit="ratio",
        baseline=1.0, watch=1.5, warn=2.0, critical=3.0, direction="up",
        tags=["P1", "M4"],
    ),
    SignalDef(
        code="INS_FUND_PCT", label="Insurance fund (% of start)", unit="%",
        baseline=100, watch=90, warn=60, critical=25, direction="down",
        tags=["M2", "M3"],
    ),
    SignalDef(
        code="BAD_DEBT_RATE", label="Bad debt rate", unit="%fund/min",
        baseline=0, watch=0.01, warn=0.01, critical=2, direction="up",
        tags=["M2"],
    ),
    SignalDef(
        code="ADL_COUNT", label="Auto-deleverage events", unit="count",
        baseline=0, watch=None, warn=None, critical=1, direction="up",
        tags=["M2"],
    ),
    SignalDef(
        code="NEG_BAL_ACCTS", label="Negative-balance accounts", unit="count",
        baseline=0, watch=None, warn=1, critical=50, direction="up",
        tags=["M3"],
    ),
    SignalDef(
        code="ORACLE_DEV", label="Oracle deviation", unit="%",
        baseline=0.05, watch=0.3, warn=0.5, critical=1.5, direction="up",
        tags=["M4"],
    ),
    SignalDef(
        code="ORACLE_AGE", label="Oracle age", unit="s",
        baseline=1, watch=3, warn=5, critical=15, direction="up",
        tags=["M4"],
    ),
    SignalDef(
        code="STBL_PX", label="Stablecoin price", unit="USD",
        baseline=1.000, watch=0.995, warn=0.985, critical=0.97, direction="down",
        tags=["S1"],
    ),
    SignalDef(
        code="SETTLE_FAIL_PCT", label="Settlement failure rate", unit="%",
        baseline=0.2, watch=1, warn=2, critical=10, direction="up",
        tags=["S2"],
    ),
    SignalDef(
        code="LP_REJECT_PCT", label="LP reject rate", unit="%",
        baseline=0.5, watch=2, warn=5, critical=20, direction="up",
        tags=["S3"],
    ),
    SignalDef(
        code="NET_EXPOSURE_PCT", label="Net exposure (% of limit)", unit="% of limit",
        baseline=20, watch=50, warn=70, critical=100, direction="up",
        tags=["S3", "M5"],
    ),
    SignalDef(
        code="WDR_QUEUE_RATIO", label="Withdrawal queue ratio", unit="%",
        baseline=5, watch=25, warn=50, critical=90, direction="up",
        tags=["S4"],
    ),
    SignalDef(
        code="INR_BASIS_PCT", label="INR/USDT basis", unit="%",
        baseline=0.2, watch=0.5, warn=1, critical=3, direction="up",
        tags=["S5"],
    ),
    SignalDef(
        code="ORDER_LATENCY_P95", label="Order latency p95", unit="ms",
        baseline=80, watch=400, warn=1000, critical=5000, direction="up",
        tags=["P2"],
    ),
    SignalDef(
        code="API_ERR_PCT", label="API error rate", unit="%",
        baseline=0.3, watch=1, warn=2, critical=10, direction="up",
        tags=["P2"],
    ),
    SignalDef(
        code="UPI_FAIL_PCT", label="UPI failure rate", unit="%",
        baseline=1, watch=3, warn=5, critical=25, direction="up",
        tags=["R1"],
    ),
    SignalDef(
        code="TICKET_RATE", label="Support ticket rate", unit="× baseline",
        baseline=1, watch=2, warn=3, critical=8, direction="up",
        tags=["I1"],
    ),
    SignalDef(
        code="SENTIMENT", label="Social sentiment", unit="−1…+1",
        baseline=0.1, watch=-0.2, warn=-0.4, critical=-0.7, direction="down",
        tags=["I1", "I2"],
    ),
    SignalDef(
        code="RUMOR_MENTIONS", label="Rumor mentions", unit="/min",
        baseline=0, watch=5, warn=20, critical=60, direction="up",
        tags=["I2"],
    ),
]

_BY_CODE: dict[str, SignalDef] = {s.code: s for s in SIGNALS}


def status_of(code: str, value: float) -> SignalStatus:
    """Return the highest matching status for `value` on signal `code`.

    Missing (`None`) thresholds are skipped. Returns `'normal'` if no
    threshold matches (or the code is unknown).
    """
    sig = _BY_CODE.get(code)
    if sig is None:
        return "normal"

    levels: list[tuple[SignalStatus, float | None]] = [
        ("critical", sig.critical),
        ("warn", sig.warn),
        ("watch", sig.watch),
    ]
    for status, threshold in levels:
        if threshold is None:
            continue
        if sig.direction == "up":
            if value >= threshold:
                return status
        else:
            if value <= threshold:
                return status
    return "normal"
