"""Classifier truth table (H2, SPEC §9.2)."""

from __future__ import annotations

import pytest

from incident.catalogue import SIGNALS
from incident.contracts import SignalFrame
from incident.rules.classifier import classify

ALL_FLAGS = (
    "cannot_close",
    "wallet_compromise_suspected",
    "regulatory_notice",
    "partner_notice",
    "media_attention",
    "stablecoin_frozen_address",
)


def make_frame(values: dict[str, float] | None = None, t: int = 0) -> SignalFrame:
    base = {s.code: float(s.baseline) for s in SIGNALS}
    base.update(values or {})
    liq = float(base.get("LIQ_RATE", 5.0))
    lar = float(base.get("LAR", 1.0))
    l_exp = liq / lar if lar else 0.0
    return SignalFrame(
        t=t,
        values=base,
        flags={code: False for code in ALL_FLAGS},
        meta={"L_obs": liq, "L_exp": l_exp},
    )


def test_market_large_move_explained_lar() -> None:
    res = classify(make_frame({"PX_CHG_5M": -6.0, "LIQ_RATE": 145.0, "LAR": 1.1}))
    assert res.verdict == "MARKET"
    assert res.lar == pytest.approx(1.1)
    assert "1.1" in res.explanation


def test_system_small_move_high_lar() -> None:
    res = classify(make_frame({"PX_CHG_5M": -2.0, "LIQ_RATE": 120.0, "LAR": 3.5}))
    assert res.verdict == "SYSTEM"


def test_pricing_high_lar_bad_oracle() -> None:
    res = classify(make_frame({"PX_CHG_5M": -1.0, "LIQ_RATE": 150.0, "LAR": 3.2, "ORACLE_DEV": 0.8}))
    assert res.verdict == "PRICING"


def test_collateral_high_lar_depeg() -> None:
    res = classify(make_frame({"PX_CHG_5M": -1.0, "LIQ_RATE": 150.0, "LAR": 2.8, "STBL_PX": 0.98}))
    assert res.verdict == "COLLATERAL"


def test_information_tickets_only() -> None:
    res = classify(make_frame({"TICKET_RATE": 4.1, "SENTIMENT": -0.3}))
    assert res.verdict == "INFORMATION"


def test_none_all_quiet() -> None:
    res = classify(make_frame({}))
    assert res.verdict == "NONE"


def test_collateral_beats_pricing_when_both_present() -> None:
    res = classify(
        make_frame({"LAR": 3.5, "STBL_PX": 0.98, "ORACLE_DEV": 2.0, "PX_CHG_5M": -1.0})
    )
    assert res.verdict == "COLLATERAL"


def test_pricing_beats_system() -> None:
    res = classify(
        make_frame({"LAR": 3.5, "ORACLE_DEV": 2.0, "PX_CHG_5M": -1.0})
    )
    assert res.verdict == "PRICING"
