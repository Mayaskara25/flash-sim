"""Every hand-written (generated) fixture must validate against the pydantic
contract models (CONTRACTS.md §8): this is what keeps
`docs/contracts/fixtures/*.json` honest as the contract evolves.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from incident.contracts import IncidentStateDTO, IncidentSummary

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "docs" / "contracts" / "fixtures"

STATE_NAMES = [
    "idle", "normal", "warning", "critical", "emergency", "stabilising", "resolved",
]


def _load(name: str) -> dict:
    path = FIXTURES_DIR / name
    assert path.exists(), f"missing fixture: {path}"
    return json.loads(path.read_text())


def test_fixtures_dir_has_no_gitkeep():
    assert not (FIXTURES_DIR / ".gitkeep").exists()


@pytest.mark.parametrize("state_name", STATE_NAMES)
def test_state_fixture_validates(state_name: str):
    data = _load(f"state_{state_name}.json")
    dto = IncidentStateDTO.model_validate(data)
    assert dto.sim.t is not None


def test_summary_fixture_validates():
    data = _load("summary_c1.json")
    summary = IncidentSummary.model_validate(data)
    assert summary.scenario_id == "C1"
    assert summary.peak_sev == 2


def test_all_state_fixtures_carry_all_21_catalogue_signals():
    from incident.catalogue import SIGNALS

    expected_codes = {s.code for s in SIGNALS}
    for name in STATE_NAMES:
        data = _load(f"state_{name}.json")
        codes = {s["code"] for s in data["signals"]}
        assert codes == expected_codes, f"state_{name}.json signal codes mismatch"


def test_critical_fixture_tells_the_c1_story():
    data = _load("state_critical.json")
    assert data["severity"]["state"] == "CRITICAL"
    tags = {t["tag"] for t in data["tags"] if t["active"]}
    assert tags == {"M1", "I1", "M2"}
    reduce_only = next(a for a in data["actions"] if a["control_id"] == "reduce_only")
    assert reduce_only["status"] == "proposed"
    assert reduce_only["what_if"] is not None


def test_emergency_fixture_has_hard_override_and_fund_at_22():
    data = _load("state_emergency.json")
    assert data["severity"]["state"] == "EMERGENCY"
    assert data["severity"]["overrides"]
    fund = next(s for s in data["signals"] if s["code"] == "INS_FUND_PCT")
    assert fund["value"] == 22


def test_stabilising_fixture_has_pending_confirmation():
    data = _load("state_stabilising.json")
    assert data["severity"]["pending"] is not None
    assert data["severity"]["pending"]["needs"] == "IC"


def test_warning_fixture_tags_m1_only():
    data = _load("state_warning.json")
    tags = {t["tag"] for t in data["tags"] if t["active"]}
    assert tags == {"M1"}


def test_log_accumulates_across_the_main_branch_states():
    lengths = [len(_load(f"state_{n}.json")["log"]) for n in ["normal", "warning", "critical", "stabilising", "resolved"]]
    assert lengths == sorted(lengths)
    assert lengths[0] >= 1
    assert lengths[-1] > lengths[0]
