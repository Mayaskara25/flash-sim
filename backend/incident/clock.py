"""Sim clock (H1). Backend-owned sim time, advanced lazily from wall-clock.

One tick = 2 sim-seconds (``TICK_S``). PLAN §3.3: the frontend polls and the
backend advances sim time from ``wall-clock × speed`` on each request — no
background threads. Wall time is injectable (``time_fn``) so tests never
sleep.

Sim time ``t`` is an int in sim-seconds; ``t = 0`` is scenario T+0 and
negative values are pre-roll.
"""

from __future__ import annotations

import time as _time
from typing import Callable, Iterator

TICK_S = 2


class SimClock:
    """Maps wall-clock seconds onto sim-seconds at ``speed``× realtime."""

    def __init__(
        self,
        speed: float = 8.0,
        t0: int = 0,
        time_fn: Callable[[], float] | None = None,
        paused: bool = False,
    ) -> None:
        if speed <= 0:
            raise ValueError("speed must be > 0")
        self._speed = float(speed)
        self._time_fn = time_fn or _time.time
        # Anchor: at wall ``_anchor_wall`` the sim time was ``_anchor_t``.
        self._anchor_wall = float(self._time_fn())
        self._anchor_t = float(t0)
        self._paused = bool(paused)
        self._paused_t = float(t0)
        # Cursor for tick enumeration: ticks with sim time > _consumed_t and
        # <= now are yielded once by ``ticks_until`` / ``pending_ticks``.
        self._consumed_t = float(t0)

    # -- state -----------------------------------------------------------
    @property
    def speed(self) -> float:
        return self._speed

    @property
    def paused(self) -> bool:
        return self._paused

    def now_t(self) -> int:
        """Current sim time in whole sim-seconds."""
        if self._paused:
            return int(self._paused_t)
        return int(self._anchor_t + (self._time_fn() - self._anchor_wall) * self._speed)

    # -- controls --------------------------------------------------------
    def pause(self) -> int:
        self._paused_t = float(self.now_t())
        self._paused = True
        return int(self._paused_t)

    def resume(self) -> int:
        if self._paused:
            self._anchor_t = float(self._paused_t)
            self._anchor_wall = float(self._time_fn())
            self._paused = False
        return self.now_t()

    def set_speed(self, speed: float) -> float:
        if speed <= 0:
            raise ValueError("speed must be > 0")
        if not self._paused:
            # Re-anchor so current sim time is preserved across the change.
            self._anchor_t = float(self.now_t())
            self._anchor_wall = float(self._time_fn())
        else:
            self._anchor_t = float(self._paused_t)
        self._speed = float(speed)
        return self._speed

    def jump(self, t: int) -> int:
        """Seek forward only (debug control, H6). Never goes backwards."""
        t = int(t)
        now = self.now_t()
        if t < now:
            raise ValueError(f"jump target T+{t} is behind current T+{now}")
        if self._paused:
            self._paused_t = float(t)
            self._anchor_t = float(t)
        else:
            self._anchor_t = float(t)
            self._anchor_wall = float(self._time_fn())
        return self.now_t()

    def reset(self, t0: int = 0) -> int:
        """Reset the clock to ``t0`` (used by session reset)."""
        self._anchor_t = float(t0)
        self._anchor_wall = float(self._time_fn())
        self._paused_t = float(t0)
        self._consumed_t = float(t0)
        return int(t0)

    # -- tick enumeration -------------------------------------------------
    def ticks_until(self, t: int) -> Iterator[int]:
        """Yield tick sim-times ``(consumed, t]`` aligned to ``TICK_S``.

        The upper bound is inclusive when it lands exactly on a tick.
        """
        t = int(t)
        start = int(self._consumed_t)
        # First tick strictly after what was consumed.
        first = (start // TICK_S) * TICK_S + TICK_S
        cur = first
        while cur <= t:
            yield cur
            cur += TICK_S
        if t > self._consumed_t:
            self._consumed_t = float(t)

    def pending_ticks(self) -> list[int]:
        """All not-yet-processed ticks up to the current sim time."""
        return list(self.ticks_until(self.now_t()))
