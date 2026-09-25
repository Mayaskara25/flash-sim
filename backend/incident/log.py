"""Append-only incident event journal."""

from .contracts import LogEntry


def time_label(t: int) -> str:
    sign = "+" if t >= 0 else "-"
    minutes, seconds = divmod(abs(t), 60)
    return f"T{sign}{minutes:02d}:{seconds:02d}"


class IncidentLog:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def append(self, *, t: int, type: str, sev: int, tags: list[str], actor: str,
               action: str, rationale: str | None = None,
               snapshot: dict[str, float] | None = None, review: str | None = None,
               approved_by: str | None = None, expires_at: int | None = None,
               ref: str | None = None) -> LogEntry:
        entry = LogEntry(id=len(self.entries) + 1, t=t, t_label=time_label(t),
                         type=type, sev=sev, scenario_tags=tags, actor=actor,
                         action=action, rationale=rationale, signal_snapshot=snapshot or {},
                         liquidation_review=review, approved_by=approved_by,
                         expires_at=expires_at, ref=ref)
        self.entries.append(entry)
        return entry
