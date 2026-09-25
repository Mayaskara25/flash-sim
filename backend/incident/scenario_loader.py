"""Scenario JSON loading + keyframe track interpolation (H1).

A scenario is a static JSON document (see ``scenarios/SCHEMA.md``). This
module validates it with pydantic and offers ``track_value`` — piecewise
linear interpolation between ``[t, value]`` keyframes, clamped outside the
defined range.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"


class BookSpec(BaseModel):
    n_traders: int = 10000
    avg_leverage: float = 14.7
    long_ratio: float = 0.72
    book_scale: float = 1.0
    insurance_fund_usd: float = 250000.0
    slippage: float = 0.35
    #: Liquidation engine throughput cap, in *executed* liquidations/min
    #: (raw book units, before `book_scale`/`LAR_MULT`). `None` (default) =
    #: unbounded — every crossing executes the tick it happens, the old
    #: behaviour. See `incident/book.py` module docstring and SCHEMA.md.
    liq_capacity_per_min: float | None = None


class ExpectedPoint(BaseModel):
    t: int
    model_config = {"extra": "allow"}  # signal code -> [lo, hi] band


class ScenarioSpec(BaseModel):
    id: str
    name: str
    description: str = ""
    preroll_s: int = 120
    duration_s: int = 3600
    seed: int = 42
    asset: str = "NVDA"
    book: BookSpec = Field(default_factory=BookSpec)
    tracks: dict[str, list[list[float]]] = Field(default_factory=dict)
    noise: dict[str, float] = Field(default_factory=dict)
    faults: dict[str, list[list[float]]] = Field(default_factory=dict)
    flags: dict[str, list[list[float]]] = Field(default_factory=dict)
    expected: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("tracks", "faults", "flags", mode="before")
    @classmethod
    def _coerce_tracks(cls, v: Any) -> Any:
        return v or {}


def interp_track(keyframes: list[list[float]], t: float) -> float:
    """Piecewise-linear interpolation; clamped outside the keyframe range."""
    if not keyframes:
        raise ValueError("empty track")
    pts = sorted(keyframes, key=lambda p: p[0])
    if t <= pts[0][0]:
        return float(pts[0][1])
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            if t1 == t0:
                return float(v1)
            frac = (t - t0) / (t1 - t0)
            return float(v0 + frac * (v1 - v0))
    return float(pts[-1][1])


class ScenarioLoader:
    """Validated scenario with track lookup helpers."""

    def __init__(self, spec: ScenarioSpec) -> None:
        self.spec = spec

    @classmethod
    def from_file(cls, path: str | Path) -> "ScenarioLoader":
        data = json.loads(Path(path).read_text())
        return cls(spec=ScenarioSpec.model_validate(data))

    @classmethod
    def from_id(cls, scenario_id: str) -> "ScenarioLoader":
        direct = SCENARIOS_DIR / f"{scenario_id}.json"
        if direct.exists():
            return cls.from_file(direct)
        # Fall back to matching the `id` field (e.g. "C1" lives in
        # `C1_black_tuesday.json`). Lets H8 name files descriptively.
        if SCENARIOS_DIR.exists():
            for path in sorted(SCENARIOS_DIR.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                except Exception:
                    continue
                if isinstance(data, dict) and data.get("id") == scenario_id:
                    return cls(spec=ScenarioSpec.model_validate(data))
        raise FileNotFoundError(f"no scenario {scenario_id!r} in {SCENARIOS_DIR}")

    # -- track access ----------------------------------------------------
    def track_value(self, code: str, t: float) -> float | None:
        """Scripted value for a catalogue ``code`` at sim time ``t``.

        Returns ``None`` when the scenario defines no track for ``code``
        (caller falls back to the catalogue baseline + noise).
        """
        kf = self.spec.tracks.get(code)
        if kf is None:
            return None
        return interp_track(kf, t)

    def fault_value(self, code: str, t: float, default: float) -> float:
        kf = self.spec.faults.get(code)
        if kf is None:
            return float(default)
        return interp_track(kf, t)

    def flag_active(self, code: str, t: float) -> bool:
        """Flags are ``[[t_start, t_end], ...]`` active windows."""
        for window in self.spec.flags.get(code, []):
            if len(window) >= 2 and window[0] <= t <= window[1]:
                return True
        return False

    def noise_sigma(self, code: str) -> float:
        return float(self.spec.noise.get(code, 0.0))


def load_scenario(scenario_id: str) -> ScenarioLoader:
    return ScenarioLoader.from_id(scenario_id)


def list_scenarios() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not SCENARIOS_DIR.exists():
        return out
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        try:
            spec = ScenarioSpec.model_validate(json.loads(path.read_text()))
        except Exception:
            continue
        out.append(
            {
                "id": spec.id,
                "name": spec.name,
                "description": spec.description,
                "duration_s": spec.duration_s,
            }
        )
    return out
