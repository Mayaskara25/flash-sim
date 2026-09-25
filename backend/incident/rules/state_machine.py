"""Incident state machine (H2, SPEC §9.3).

Upward moves are automatic; downward moves from CRITICAL/EMERGENCY need
5 sim-minutes below band plus IC confirmation (hysteresis, SPEC §3).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from incident.catalogue import SIGNALS, status_of
from incident.contracts import IncidentState, SignalFrame

from .history import SignalHistory
from .severity import SeverityResult

STEPDOWN_S = 300  # 5 sim-min below band before a step-down is proposed
RESOLVE_S = 900  # 15 sim-min below warn before resolve is proposed

# PLAN §3 decision #13: the STABILISING -> RESOLVED check requires "all
# signals < warn for 15 min", which can never fire for INS_FUND_PCT if the
# fund settles below its 60% warn line without a top-up (e.g. ~40%, well
# above the 25% critical override but still "warn" forever). For the
# resolve check ONLY, INS_FUND_PCT instead counts as settled once it is
# above critical (guaranteed here: a critical reading already forces
# STABILISING -> CRITICAL before this check runs) and flat -- its absolute
# change over the trailing 15 sim-min is under FUND_FLAT_PP -- matching
# SPEC M2's exit condition ("INS_FUND_PCT stable for 15 min"). Every other
# signal keeps the plain "< warn" requirement.
FUND_CODE = "INS_FUND_PCT"
FUND_FLAT_PP = 1.0

_RANK: dict[str, int] = {
    "NORMAL": 0,
    "WATCH": 1,
    "WARNING": 2,
    "CRITICAL": 3,
    "EMERGENCY": 4,
}

_SEV_OF: dict[IncidentState, int] = {
    "EMERGENCY": 1,
    "CRITICAL": 2,
    "WARNING": 3,
    "WATCH": 4,
    "NORMAL": 4,
    "STABILISING": 2,  # replaced by pre-stabilising SEV at runtime
    "RESOLVED": 4,
}

_SEV_TO_STATE: dict[int, IncidentState] = {
    1: "EMERGENCY",
    2: "CRITICAL",
    3: "WARNING",
    4: "WATCH",
}


def sev_of_state(state: IncidentState, prior_sev: int = 2) -> int:
    """CONTRACTS §1 state → SEV mapping.

    STABILISING keeps the SEV of the state it came from until confirmed
    down; callers pass it via `prior_sev`.
    """
    if state == "STABILISING":
        return prior_sev
    return _SEV_OF[state]


@dataclass
class TransitionEvent:
    from_state: IncidentState
    to_state: IncidentState
    t: int


@dataclass
class PendingStep:
    kind: str  # 'stepdown' | 'resolve'
    from_state: IncidentState
    to_state: IncidentState
    eligible_since_t: int


@dataclass
class StateMachine:
    """Tracks incident state across ticks. Start with `StateMachine()`."""

    state: IncidentState = "NORMAL"
    since_t: int = 0
    pending: PendingStep | None = None
    pre_stabilising_sev: int = 2
    _below_since: int | None = None
    _stable_below_since: int | None = None
    log: list[TransitionEvent] = field(default_factory=list)
    # Rolling INS_FUND_PCT samples for the resolve-check flatness rule
    # (decision #13). Recorded every `step()` call, in any state, so the
    # trailing-15-min window is accurate by the time STABILISING is reached.
    _fund_hist: deque[tuple[int, float]] = field(default_factory=deque)

    # -- target ---------------------------------------------------------
    def target(
        self, frame: SignalFrame, sev: SeverityResult, history: SignalHistory | None = None
    ) -> IncidentState:
        _ = history
        worst = "normal"
        for sig in SIGNALS:
            v = frame.values.get(sig.code)
            if v is None:
                continue
            st = status_of(sig.code, float(v))
            if st == "critical":
                worst = "critical"
                break
            if st == "warn":
                worst = "warn"
            elif st == "watch" and worst == "normal":
                worst = "watch"
        s = sev.score
        if s >= 70 or sev.overrides:
            return "EMERGENCY"
        if worst == "critical" or s >= 50:
            return "CRITICAL"
        if worst == "warn" or s >= 30:
            return "WARNING"
        if worst == "watch":
            return "WATCH"
        return "NORMAL"

    # -- fund flatness (decision #13) ------------------------------------
    def _record_fund(self, t: int, frame: SignalFrame) -> None:
        v = frame.values.get(FUND_CODE)
        if v is None:
            return
        self._fund_hist.append((t, float(v)))
        cutoff = t - RESOLVE_S - 120  # small buffer past the window we need
        while len(self._fund_hist) > 1 and self._fund_hist[0][0] < cutoff:
            self._fund_hist.popleft()

    def _fund_settled(self, t: int, current: float) -> bool:
        """True if INS_FUND_PCT's absolute change over the trailing
        `RESOLVE_S` is under `FUND_FLAT_PP`. Requires a sample at or before
        `t - RESOLVE_S` (full window coverage), same rule as
        `SignalHistory.held`."""
        if not self._fund_hist or self._fund_hist[0][0] > t - RESOLVE_S:
            return False
        target = t - RESOLVE_S
        then = self._fund_hist[0][1]
        for ht, hv in self._fund_hist:
            if ht <= target:
                then = hv
            else:
                break
        return abs(current - then) < FUND_FLAT_PP

    # -- stepping --------------------------------------------------------
    def step(
        self, t: int, sev: SeverityResult, frame: SignalFrame
    ) -> tuple[IncidentState, list[TransitionEvent]]:
        events: list[TransitionEvent] = []
        self._record_fund(t, frame)
        if self.state == "RESOLVED":
            return self.state, events

        if self.state == "STABILISING":
            events.extend(self._step_stabilising(t, frame))
            return self.state, events

        tgt = self.target(frame, sev)
        cur_rank = _RANK[self.state]
        tgt_rank = _RANK[tgt]

        if tgt_rank > cur_rank:
            events.extend(self._move(t, tgt))
            return self.state, events
        if tgt_rank == cur_rank:
            self._below_since = None
            # A sustained recovery clears a stale pending proposal.
            if self.pending is not None and self.state in ("CRITICAL", "EMERGENCY"):
                self.pending = None
            return self.state, events

        # Target below current: hysteresis.
        if self._below_since is None:
            self._below_since = t
        if self.state in ("EMERGENCY", "CRITICAL"):
            if t - self._below_since >= STEPDOWN_S and self.pending is None:
                self.pending = PendingStep(
                    kind="stepdown",
                    from_state=self.state,
                    to_state="STABILISING",
                    eligible_since_t=t,
                )
            return self.state, events
        # WARNING / WATCH / NORMAL step down automatically after 300 s.
        if t - self._below_since >= STEPDOWN_S:
            events.extend(self._move(t, tgt))
        return self.state, events

    def _step_stabilising(
        self, t: int, frame: SignalFrame
    ) -> list[TransitionEvent]:
        events: list[TransitionEvent] = []
        recritical = any(
            (v := frame.values.get(sig.code)) is not None
            and status_of(sig.code, float(v)) == "critical"
            for sig in SIGNALS
        )
        if recritical:
            self.pending = None
            self._stable_below_since = None
            events.extend(self._move(t, "CRITICAL"))
            return events
        def _settled(sig) -> bool:
            v = frame.values.get(sig.code)
            if v is None:
                return True
            if sig.code == FUND_CODE:
                return self._fund_settled(t, float(v))
            return status_of(sig.code, float(v)) not in ("warn", "critical")

        all_below_warn = all(_settled(sig) for sig in SIGNALS)
        if all_below_warn:
            if self._stable_below_since is None:
                self._stable_below_since = t
            if (
                t - self._stable_below_since >= RESOLVE_S
                and self.pending is None
            ):
                self.pending = PendingStep(
                    kind="resolve",
                    from_state="STABILISING",
                    to_state="RESOLVED",
                    eligible_since_t=t,
                )
        else:
            self._stable_below_since = None
        return events

    def _move(self, t: int, to_state: IncidentState) -> list[TransitionEvent]:
        if to_state == self.state:
            return []
        if self.state in ("CRITICAL", "EMERGENCY") and to_state == "STABILISING":
            self.pre_stabilising_sev = sev_of_state(self.state)
        ev = TransitionEvent(from_state=self.state, to_state=to_state, t=t)
        self.state = to_state
        self.since_t = t
        self._below_since = None
        self.pending = None
        if to_state != "STABILISING":
            self._stable_below_since = None
        self.log.append(ev)
        return [ev]

    # -- operator ---------------------------------------------------------
    def confirm(self, actor: str, t: int) -> list[TransitionEvent]:
        """Confirm a pending step-down / resolve. Only IC may confirm."""
        if actor != "IC":
            raise ValueError("Only IC can confirm a step-down or resolve")
        if self.pending is None:
            raise ValueError("No pending transition to confirm")
        to_state = self.pending.to_state
        return self._move(t, to_state)

    def manual_raise(self, sev: int, t: int) -> list[TransitionEvent]:
        """Manual severity raise (any time). Never lowers the state."""
        if sev not in (1, 2, 3, 4):
            raise ValueError(f"Invalid SEV: {sev}")
        tgt = _SEV_TO_STATE[sev]
        if self.state in ("STABILISING", "RESOLVED"):
            return []
        if _RANK[tgt] > _RANK[self.state]:
            return self._move(t, tgt)
        return []
