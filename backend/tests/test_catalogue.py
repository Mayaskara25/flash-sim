from incident.catalogue import SIGNALS, status_of


def test_catalogue_has_21_signals():
    assert len(SIGNALS) == 21


def test_catalogue_codes_unique():
    codes = [s.code for s in SIGNALS]
    assert len(codes) == len(set(codes))


def test_status_of_unknown_code_is_normal():
    assert status_of("NOT_A_SIGNAL", 1e9) == "normal"


def test_status_of_up_direction_thresholds():
    # LIQ_RATE: watch 30, warn 100, critical 300, direction up
    assert status_of("LIQ_RATE", 0) == "normal"
    assert status_of("LIQ_RATE", 29.99) == "normal"
    assert status_of("LIQ_RATE", 30) == "watch"
    assert status_of("LIQ_RATE", 99.99) == "watch"
    assert status_of("LIQ_RATE", 100) == "warn"
    assert status_of("LIQ_RATE", 299.99) == "warn"
    assert status_of("LIQ_RATE", 300) == "critical"
    assert status_of("LIQ_RATE", 1000) == "critical"


def test_status_of_down_direction_thresholds():
    # PX_CHG_5M: watch -2, warn -5, critical -10, direction down
    assert status_of("PX_CHG_5M", 0) == "normal"
    assert status_of("PX_CHG_5M", -1.99) == "normal"
    assert status_of("PX_CHG_5M", -2) == "watch"
    assert status_of("PX_CHG_5M", -4.99) == "watch"
    assert status_of("PX_CHG_5M", -5) == "warn"
    assert status_of("PX_CHG_5M", -9.99) == "warn"
    assert status_of("PX_CHG_5M", -10) == "critical"
    assert status_of("PX_CHG_5M", -50) == "critical"


def test_status_of_skips_none_thresholds():
    # ADL_COUNT has no watch/warn, only baseline 0 and critical 1.
    assert status_of("ADL_COUNT", 0) == "normal"
    assert status_of("ADL_COUNT", 0.5) == "normal"
    assert status_of("ADL_COUNT", 1) == "critical"

    # NEG_BAL_ACCTS has no watch, only warn (1) and critical (50).
    assert status_of("NEG_BAL_ACCTS", 0) == "normal"
    assert status_of("NEG_BAL_ACCTS", 1) == "warn"
    assert status_of("NEG_BAL_ACCTS", 49) == "warn"
    assert status_of("NEG_BAL_ACCTS", 50) == "critical"


def test_status_of_returns_highest_matching_level():
    # A value that satisfies watch, warn and critical simultaneously (up
    # direction, all thresholds crossed) must report 'critical', not the
    # first one found.
    assert status_of("LIQ_RATE", 1_000_000) == "critical"
