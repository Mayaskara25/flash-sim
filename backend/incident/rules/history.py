"""Rolling signal history (H2).

`SignalHistory` is a small ring buffer of the last 15 sim-minutes of
`SignalFrame`s. Frames themselves are memoryless (CONTRACTS §3); the rules
engine keeps its own history here for duration rules ("STBL_PX < 0.97 for
5 min", "cannot_close for 3 min") and for the velocity dimension.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from incident.catalogue import SIGNALS
from incident.contracts import SignalFrame

# 15 sim-minutes of history (H2 handoff).
HISTORY_S = 15 * 60

_BY_CODE = {s.code: s for s in SIGNALS}


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def stress_of(code: str, value: float) -> float:
    """Position of `value` between baseline (0) and critical (1).

    For `direction == 'up'`: (value - baseline) / (critical - baseline).
    For `direction == 'down'`: (baseline - value) / (baseline - critical).
    Clipped to [0, 1]. Unknown codes or degenerate thresholds return 0.
    """
    sig = _BY_CODE.get(code)
    if sig is None or sig.critical is None:
        return 0.0
    try:
        if sig.direction == "up":
            denom = sig.critical - sig.baseline
            if denom <= 0:
                return 0.0
            return _clip01((value - sig.baseline) / denom)
        denom = sig.baseline - sig.critical
        if denom <= 0:
            return 0.0
        return _clip01((sig.baseline - value) / denom)
    except (TypeError, ValueError):
        return 0.0


class SignalHistory:
    """Ring buffer of recent frames, ordered by insertion (t ascending)."""

    def __init__(self, window_s: int = HISTORY_S) -> None:
        self.window_s = window_s
        self._frames: deque[SignalFrame] = deque()

    def __len__(self) -> int:
        return len(self._frames)

    @property
    def latest_t(self) -> int | None:
        if not self._frames:
            return None
        return self._frames[-1].t

    def add(self, frame: SignalFrame) -> None:
        self._frames.append(frame)
        cutoff = frame.t - self.window_s
        while self._frames and self._frames[0].t < cutoff:
            self._frames.popleft()

    def frames_in(self, start_t: int, end_t: int) -> list[SignalFrame]:
        return [f for f in self._frames if start_t <= f.t <= end_t]

    def value_at(self, code: str, t: int) -> float | None:
        """Latest value for `code` at or before `t`, else None."""
        best: float | None = None
        for f in self._frames:
            if f.t <= t and code in f.values:
                best = f.values[code]
            elif f.t > t:
                break
        return best

    def flag_at(self, code: str, t: int) -> bool | None:
        best: bool | None = None
        for f in self._frames:
            if f.t <= t and code in f.flags:
                best = f.flags[code]
            elif f.t > t:
                break
        return best

    def held(
        self,
        code: str,
        pred: Callable[[float], bool],
        seconds: int,
        now_t: int | None = None,
    ) -> bool:
        """True if `pred(value)` held continuously over the last `seconds`.

        Requires coverage of the full window: the earliest frame at or
        before `now - seconds` must exist, and every frame in
        `(now - seconds, now]` must satisfy `pred`. With 2 s ticks, an
        N-second rule flips at N s, not N-2 s.
        """
        now = self.latest_t if now_t is None else now_t
        if now is None or not self._frames:
            return False
        start = now - seconds
        # Need a frame at or before the window start for full coverage.
        covered = any(f.t <= start for f in self._frames)
        if not covered:
            return False
        window = [f for f in self._frames if start < f.t <= now]
        if not window:
            return False
        for f in window:
            if code not in f.values:
                return False
            if not pred(f.values[code]):
                return False
        return True

    def flag_held(self, code: str, seconds: int, now_t: int | None = None) -> bool:
        """True if boolean flag `code` was set over the last `seconds`."""
        now = self.latest_t if now_t is None else now_t
        if now is None or not self._frames:
            return False
        start = now - seconds
        covered = any(f.t <= start for f in self._frames)
        if not covered:
            return False
        window = [f for f in self._frames if start < f.t <= now]
        if not window:
            return False
        return all(f.flags.get(code, False) for f in window)

    def stress(self, code: str) -> float:
        """Current stress (0..1) for `code`, 0 when no frames yet."""
        if not self._frames:
            return 0.0
        value = self._frames[-1].values.get(code)
        if value is None:
            return 0.0
        return stress_of(code, value)

    def stress_at(self, code: str, t: int) -> float:
        value = self.value_at(code, t)
        if value is None:
            return 0.0
        return stress_of(code, value)
