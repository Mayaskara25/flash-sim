"""Human-approved protective controls from SPEC §9.4.

The effects are simulation instructions, never real trading commands. H1
applies them only after H5 records an operator's approval.
"""

from incident.contracts import ControlDef, Effect


def _control(id: str, label: str, reduces: str, tradeoff: str, tags: list[str],
             effects: list[Effect], time_box_s: int | None = None,
             params: dict[str, float] | None = None) -> ControlDef:
    return ControlDef(id, label, reduces, tradeoff, tags, time_box_s, effects, params or {})


CONTROLS: dict[str, ControlDef] = {c.id: c for c in [
    _control("leverage_cap", "Lower max leverage on new positions", "Future cascade size", "Revenue and user complaints", ["M1", "M2"], [Effect("sim.max_leverage", "set", 3)], params={"max_leverage": 3}),
    _control("reduce_only", "Reduce-only mode per instrument", "New exposure and hedge gap", "Users cannot open trades", ["M2", "S3", "P1"], [Effect("sim.new_exposure", "set", 0), Effect("LIQ_RATE", "mult", 0.6, 120)]),
    _control("raise_mm", "Raise maintenance margin / partial liquidation", "Cascade speed", "More margin calls", ["M2", "M6"], [Effect("sim.maintenance_mult", "set", 1.3)], params={"maintenance_mult": 1.3}),
    _control("pause_liqs", "Pause liquidations on affected instruments", "Wrongful liquidations", "Bad debt may grow during pause", ["M4", "P1", "P2"], [Effect("sim.liquidations_paused", "set", 1)], time_box_s=600),
    _control("fallback_feed", "Switch to fallback median price feed", "Bad marks", "Slight price lag", ["M4"], [Effect("ORACLE_DEV", "set", 0.1, 30), Effect("ORACLE_AGE", "set", 1, 30)]),
    _control("collateral_haircut", "Apply smoothed collateral haircut", "Treasury gap during depeg", "Some users may be liquidated", ["S1"], [Effect("LIQ_RATE", "mult", 0.7)], params={"smoothing_minutes": 30}),
    _control("pause_deposits", "Pause deposits in affected stablecoin", "Toxic inflows", "Users cannot top up with that coin", ["S1", "S2"], [Effect("SETTLE_FAIL_PCT", "mult", 0.8)]),
    _control("ins_fund_topup", "Top up insurance fund", "ADL risk", "Uses company capital", ["M2", "M3"], [Effect("sim.fund_topup_pct", "add", 20)], params={"topup_pct": 20}),
    _control("load_shed", "Shed non-essential API load", "Trading-engine overload", "Non-core features unavailable", ["P2"], [Effect("ORDER_LATENCY_P95", "mult", 0.3, 90), Effect("API_ERR_PCT", "mult", 0.3, 90)]),
    _control("freeze_hot_wallet", "Freeze hot-wallet signing", "Theft", "Withdrawals stop", ["P3"], [Effect("WDR_QUEUE_RATIO", "add", 20)]),
]}
