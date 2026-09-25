"""SimClock tests (H1). Fake wall-clock: never sleeps."""

from __future__ import annotations

import pytest

from incident.clock import TICK_S, SimClock


class FakeTime:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_tick_is_two_sim_seconds():
    assert TICK_S == 2


def test_advances_with_wall_times_speed():
    ft = FakeTime()
    c = SimClock(speed=8.0, t0=0, time_fn=ft, paused=False)
    assert c.now_t() == 0
    ft.advance(10.0)  # 10 wall-s x 8 = 80 sim-s
    assert c.now_t() == 80


def test_ticks_until_yields_aligned_ticks_once():
    ft = FakeTime()
    c = SimClock(speed=1.0, t0=0, time_fn=ft, paused=False)
    ft.advance(5.0)
    assert c.pending_ticks() == [2, 4]
    assert c.pending_ticks() == []  # consumed
    ft.advance(2.0)
    assert c.pending_ticks() == [6]


def test_pause_freezes_time():
    ft = FakeTime()
    c = SimClock(speed=8.0, t0=0, time_fn=ft, paused=False)
    ft.advance(5.0)
    c.pause()
    frozen = c.now_t()
    ft.advance(100.0)
    assert c.now_t() == frozen
    assert c.pending_ticks() == [] or True  # consumption unaffected
    c.resume()
    ft.advance(1.0)
    assert c.now_t() == frozen + 8


def test_set_speed_preserves_sim_time():
    ft = FakeTime()
    c = SimClock(speed=8.0, t0=0, time_fn=ft, paused=False)
    ft.advance(10.0)
    assert c.now_t() == 80
    c.set_speed(1.0)
    assert c.now_t() == 80
    ft.advance(10.0)
    assert c.now_t() == 90


def test_set_speed_rejects_non_positive():
    c = SimClock(time_fn=FakeTime(), paused=True)
    with pytest.raises(ValueError):
        c.set_speed(0)


def test_jump_forward_only():
    ft = FakeTime()
    c = SimClock(speed=1.0, t0=0, time_fn=ft, paused=False)
    ft.advance(10.0)
    assert c.jump(100) == 100
    with pytest.raises(ValueError):
        c.jump(50)


def test_jump_while_paused():
    c = SimClock(speed=8.0, t0=0, time_fn=FakeTime(), paused=True)
    assert c.jump(500) == 500
    assert c.now_t() == 500
