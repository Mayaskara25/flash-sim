"""Collapsed alert cards (H2).

One `AlertCard` per (signal, level). Repeated crossings of the same level
increment `count` and update `last_t`; an escalation from warn to critical
creates a new card and supersedes the warn card (it freezes until the signal
drops back below warn and re-crosses).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from incident.catalogue import SIGNALS
from incident.catalogue import status_of
from incident.contracts import SignalFrame

ALERT_LEVELS = ("warn", "critical")


@dataclass
class AlertCardState:
    id: str
    signal: str
    level: str  # 'warn' | 'critical'
    count: int
    first_t: int
    last_t: int
    acknowledged_by: str | None = None
    superseded: bool = False


@dataclass
class AlertManager:
    """Tracks per-(signal, level) cards across ticks."""

    cards: dict[str, AlertCardState] = field(default_factory=dict)
    _level_now: dict[str, str | None] = field(default_factory=dict)

    def update(self, t: int, frame: SignalFrame) -> list[AlertCardState]:
        for sig in SIGNALS:
            v = frame.values.get(sig.code)
            level = (
                status_of(sig.code, float(v))
                if v is not None
                else "normal"
            )
            alert_level: str | None = (
                level if level in ALERT_LEVELS else None
            )
            prev = self._level_now.get(sig.code)
            if alert_level == prev:
                continue
            if prev == "warn" and alert_level is None:
                # Signal cooled: allow a future re-cross to count again and
                # un-supersede the warn card.
                card = self.cards.get(f"{sig.code}:warn")
                if card is not None:
                    card.superseded = False
            if alert_level == "warn":
                key = f"{sig.code}:warn"
                card = self.cards.get(key)
                if card is None:
                    self.cards[key] = AlertCardState(
                        id=key,
                        signal=sig.code,
                        level="warn",
                        count=1,
                        first_t=t,
                        last_t=t,
                    )
                elif not card.superseded:
                    card.count += 1
                    card.last_t = t
                else:
                    # Re-cross after a superseded escalation: revive.
                    card.superseded = False
                    card.count += 1
                    card.last_t = t
            elif alert_level == "critical":
                key = f"{sig.code}:critical"
                card = self.cards.get(key)
                if card is None:
                    self.cards[key] = AlertCardState(
                        id=key,
                        signal=sig.code,
                        level="critical",
                        count=1,
                        first_t=t,
                        last_t=t,
                    )
                else:
                    card.count += 1
                    card.last_t = t
                warn_card = self.cards.get(f"{sig.code}:warn")
                if warn_card is not None:
                    warn_card.superseded = True
            self._level_now[sig.code] = alert_level
        return sorted(self.cards.values(), key=lambda c: (c.first_t, c.id))

    def ack(self, card_id: str, actor: str) -> AlertCardState:
        card = self.cards.get(card_id)
        if card is None:
            raise ValueError(f"Unknown alert: {card_id}")
        card.acknowledged_by = actor
        return card
