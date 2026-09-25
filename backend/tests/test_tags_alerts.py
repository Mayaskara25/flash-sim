"""Tags + alert cards (H2, SPEC §4 / §8)."""

from __future__ import annotations

import pytest

from incident.catalogue import SIGNALS
from incident.contracts import SignalFrame
from incident.rules.alerts import AlertManager
from incident.rules.tags import TagTracker, active_triggers, priority_order

ALL_FLAGS = (
    "cannot_close",
    "wallet_compromise_suspected",
    "regulatory_notice",
    "partner_notice",
    "media_attention",
    "stablecoin_frozen_address",
)


def make_frame(
    values: dict[str, float] | None = None,
    flags: dict[str, bool] | None = None,
    t: int = 0,
) -> SignalFrame:
    base = {s.code: float(s.baseline) for s in SIGNALS}
    base.update(values or {})
    full_flags = {code: False for code in ALL_FLAGS}
    full_flags.update(flags or {})
    return SignalFrame(t=t, values=base, flags=full_flags, meta={})


# -- tags ----------------------------------------------------------------------

def test_warn_signal_activates_its_catalogue_tags() -> None:
    frame = make_frame({"TICKET_RATE": 4.0})  # warn → I1
    assert "I1" in active_triggers(frame, "INFORMATION")


def test_liquidation_signals_follow_verdict_market() -> None:
    frame = make_frame({"LIQ_RATE": 400.0, "LAR": 1.1, "PX_CHG_5M": -8.0})
    assert "M1" in active_triggers(frame, "MARKET")
    assert "P1" not in active_triggers(frame, "MARKET")


def test_liquidation_signals_follow_verdict_system() -> None:
    frame = make_frame({"LIQ_RATE": 150.0, "LAR": 3.5, "PX_CHG_5M": -1.0})
    triggers = active_triggers(frame, "SYSTEM")
    assert "P1" in triggers
    assert "M1" not in triggers


def test_liquidation_verdict_pricing_and_collateral() -> None:
    frame = make_frame({"LIQ_RATE": 150.0, "LAR": 3.2})
    assert "M4" in active_triggers(frame, "PRICING")
    assert "S1" in active_triggers(frame, "COLLATERAL")


def test_market_plus_weak_fund_also_tags_m2() -> None:
    fund_weak = make_frame(
        {"LIQ_RATE": 400.0, "LAR": 1.1, "INS_FUND_PCT": 55.0, "BAD_DEBT_RATE": 0.3}
    )
    assert "M2" in active_triggers(fund_weak, "MARKET")
    fund_ok = make_frame({"LIQ_RATE": 400.0, "LAR": 1.1, "INS_FUND_PCT": 97.0})
    assert "M2" not in active_triggers(fund_ok, "MARKET")


def test_flags_activate_security_tags() -> None:
    assert "P3" in active_triggers(make_frame(flags={"wallet_compromise_suspected": True}), "NONE")
    assert "P2" in active_triggers(make_frame(flags={"cannot_close": True}), "NONE")
    assert "R2" in active_triggers(make_frame(flags={"regulatory_notice": True}), "NONE")


def test_tracker_remembers_first_t_and_peak() -> None:
    tr = TagTracker()
    out = tr.update(0, make_frame({"LIQ_RATE": 400.0, "LAR": 1.1, "PX_CHG_5M": -8.0}), "MARKET", 3)
    m1 = next(i for i in out if i.tag == "M1")
    assert m1.first_t == 0 and m1.peak_sev == 3 and m1.active
    # Later tick with the trigger gone: still listed, inactive, peak kept.
    out2 = tr.update(100, make_frame({}), "NONE", 4)
    m1b = next(i for i in out2 if i.tag == "M1")
    assert not m1b.active
    assert m1b.first_t == 0 and m1b.peak_sev == 3


def test_priority_order_security_first_comms_last() -> None:
    ordered = priority_order(["I1", "M1", "P3", "M2"])
    assert ordered == ["P3", "M2", "I1", "M1"]


# -- alerts ---------------------------------------------------------------------

def test_repeated_warn_crossings_collapse_into_one_card() -> None:
    am = AlertManager()
    am.update(0, make_frame({"LIQ_RATE": 5.0}))
    am.update(2, make_frame({"LIQ_RATE": 120.0}))
    am.update(4, make_frame({"LIQ_RATE": 5.0}))
    cards = am.update(6, make_frame({"LIQ_RATE": 150.0}))
    warn = next(c for c in cards if c.id == "LIQ_RATE:warn")
    assert warn.count == 2
    assert warn.first_t == 2
    assert warn.last_t == 6


def test_escalation_creates_critical_card_and_supersedes_warn() -> None:
    am = AlertManager()
    am.update(0, make_frame({"LIQ_RATE": 120.0}))
    cards = am.update(2, make_frame({"LIQ_RATE": 400.0}))
    crit = next(c for c in cards if c.id == "LIQ_RATE:critical")
    warn = next(c for c in cards if c.id == "LIQ_RATE:warn")
    assert crit.count == 1 and crit.first_t == 2
    assert warn.superseded


def test_ack_records_actor() -> None:
    am = AlertManager()
    am.update(0, make_frame({"LIQ_RATE": 120.0}))
    card = am.ack("LIQ_RATE:warn", "IC")
    assert card.acknowledged_by == "IC"
    with pytest.raises(ValueError):
        am.ack("NOPE:warn", "IC")
