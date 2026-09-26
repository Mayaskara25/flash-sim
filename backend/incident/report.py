"""Small dependency-free PDF renderer for the simulated incident record.

The app deliberately generates an incident report, not a trading report.  A
minimal PDF writer keeps the demo self-contained and avoids a heavyweight
reporting dependency for one structured operational export.
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone

from .command import build_command
from .log import time_label


PAGE_W, PAGE_H = 595, 842
LEFT, TOP, BOTTOM = 44, 790, 46

# The renderer only embeds the base-14 Helvetica font, so text is encoded as
# ASCII. Several strings elsewhere in the incident model use Unicode
# punctuation (arrows for transitions, the multiplication sign for ratios,
# the rupee sign for INR amounts, curly quotes, dashes...). Encoding those
# straight to ASCII with `errors="ignore"` used to silently drop the
# character instead of representing it, e.g. "CRITICAL -> EMERGENCY" became
# "CRITICAL  EMERGENCY". Transliterate first so nothing is silently lost.
_ASCII_MAP = {
    "→": "->", "←": "<-",
    "≤": "<=", "≥": ">=",
    "–": "-", "—": "-",
    "₹": "INR",
    "×": "x",
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "…": "...",
    "·": "-",
    "−": "-",
}


# Mirrors frontend/src/incident/components/AssumptionsPanel.tsx — keep the
# two lists in sync if either changes.
_ASSUMPTIONS = [
    "MochaTrade model: INR via UPI -> USDT/USDC custodial wallet -> leveraged futures and options; mixed A-book/B-book hedging.",
    "All thresholds, weights and baselines are simulation values, not MochaTrade production figures.",
    "Insurance fund exists and starts at a fixed simulated amount.",
    "Three roles: Incident Commander, Tech Lead, Comms/Support lead.",
    "Signals are simulated; real exchange feeds, ticketing and social listening are outside this demo.",
    "Protective controls are proposed by the tool and executed only on human approval.",
    "Regulatory handling (R2) is escalated to founders; the tool only flags and records it.",
    "Forecasts are simulated projections, not market forecasts or production risk estimates.",
]


def _ascii(value: object) -> str:
    text = str(value)
    for unicode_char, replacement in _ASCII_MAP.items():
        text = text.replace(unicode_char, replacement)
    return text.encode("ascii", "ignore").decode("ascii")


def _pdf_text(value: object) -> str:
    text = _ascii(value)
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(value: object, width: int = 89) -> list[str]:
    # Escape only at the final PDF text operation.  Escaping here as well
    # would render literal backslashes before parentheses after wrapping.
    raw = _ascii(value)
    return textwrap.wrap(raw, width=width, break_long_words=False) or [""]


class _ReportPage:
    def __init__(self, number: int) -> None:
        self.number = number
        self.y = TOP
        self.ops = ["q", "0.12 0.19 0.29 rg", f"0 {PAGE_H - 32} {PAGE_W} 32 re f", "Q"]
        self.text("MochaTrade / OPERATIONS", 44, PAGE_H - 21, 8, "0.95 0.97 1 rg")
        self.text(f"SIMULATED INCIDENT RECORD  |  PAGE {number}", 355, PAGE_H - 21, 7, "0.95 0.97 1 rg")

    def text(self, value: object, x: float, y: float, size: float = 9, color: str = "0.12 0.15 0.20 rg") -> None:
        self.ops.append(f"BT /F1 {size} Tf {color} 1 0 0 1 {x:.1f} {y:.1f} Tm ({_pdf_text(value)}) Tj ET")

    def rule(self) -> None:
        self.ops.append(f"0.85 0.88 0.91 RG {LEFT} {self.y:.1f} m {PAGE_W - LEFT} {self.y:.1f} l S")
        self.y -= 10

    def heading(self, value: str) -> None:
        if self.y < BOTTOM + 28:
            return
        self.text(value.upper(), LEFT, self.y, 10, "0.12 0.19 0.29 rg")
        self.y -= 7
        self.rule()

    def line(self, value: object, *, indent: int = 0, size: float = 8.7, color: str = "0.12 0.15 0.20 rg") -> bool:
        rows = _wrap(value)
        if self.y - len(rows) * 12 < BOTTOM:
            return False
        for row in rows:
            self.text(row, LEFT + indent, self.y, size, color)
            self.y -= 12
        return True

    def content(self) -> bytes:
        self.text("Research prototype - modelled figures only; not a production trading record.", LEFT, 28, 7, "0.38 0.42 0.47 rg")
        return "\n".join(self.ops).encode("ascii", "ignore")


def _build_pdf(pages: list[_ReportPage]) -> bytes:
    objects: list[bytes] = []
    # Catalog, Pages tree and font.  Page objects/content streams follow.
    kids = " ".join(f"{4 + index * 2} 0 R" for index in range(len(pages)))
    objects.extend([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ])
    for index, page in enumerate(pages):
        content_id = 5 + index * 2
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        content = page.content()
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def build_pdf(session) -> bytes:
    """Render the current journal and modelled command evidence as a PDF."""
    command = build_command(session)
    summary = session.summary()
    pages: list[_ReportPage] = [_ReportPage(1)]
    page = pages[-1]

    def ensure(lines: int = 4) -> _ReportPage:
        nonlocal page
        if page.y - lines * 12 < BOTTOM:
            page = _ReportPage(len(pages) + 1)
            pages.append(page)
        return page

    scenario = session.scenario.spec.name if session.started else "No scenario started"
    end_t = session.frame.t if session.started and session.frame else 0
    duration = max(0, end_t)
    page.text("FLASH CRASH INCIDENT REPORT", LEFT, page.y, 20, "0.12 0.19 0.29 rg")
    page.y -= 26
    page.line(f"Scenario: {scenario}  |  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", size=9)
    page.line("Classification: Simulated research prototype. All positions, thresholds and evidence are modelled.", size=8.5, color="0.38 0.12 0.12 rg")
    page.y -= 6

    page.heading("1. Incident overview")
    page.line(f"Start: T+00:00  |  End/current: {time_label(end_t)}  |  Duration: {duration // 60} min {duration % 60:02d} sec")
    page.line(f"Current severity: {command.risk_level}  |  Peak cascade score: {session.peak_cascade_score:.1f}/100  |  Peak SEV-{summary.peak_sev}")
    page.line(f"First priority at report time: {command.first_priority}")

    page.heading("2. Market impact")
    peak_liq, peak_liq_t = session.peaks.get("LIQ_RATE", (command.liquidation_rate, end_t))
    page.line(f"5-minute price change: {command.px_chg:.2f}%")
    page.line(f"Modelled liquidity change: {command.liquidity_change:.1f}%  |  Peak liquidation rate: {peak_liq:.1f}/min at {time_label(peak_liq_t)}")
    page.line("Volume: modelled liquidation throughput only; no production market-volume claim is made.")

    page.heading("3. Liquidation analysis")
    book = session.generator.book if session.started and session.generator else None
    total_liqs = int(book.n_liquidated_raw) if book else 0
    escalated = sum(1 for row in (command.cluster.executions if command.cluster else []) if row.status == "escalated")
    page.line(f"Total modelled liquidations: {total_liqs:,}  |  Flagged executions: {command.abnormal_liquidations}  |  Escalated executions: {escalated}")
    if command.cluster:
        page.line(f"Cluster {command.cluster.id} ({command.cluster.asset}): {command.cluster.why}")

    page.heading("4. Financial exposure")
    if book:
        gross = float((book.entry * book.qty).sum()) * float(book.book_scale)
        page.line(f"Gross modelled exposure: ${gross:,.0f}")
    else:
        page.line("Gross modelled exposure: unavailable before a scenario begins.")
    page.line(f"Net modelled exposure: {command.exposure_pct:.1f}% of configured limit")
    page.line(f"Near modelled liquidation thresholds: {command.near_liquidation:,} positions")
    page.line("Scenario exposure: analysis is simulated and does not represent a predicted loss or production intervention.")

    page.heading("5. Major decisions")
    decisions = summary.decisions or []
    if decisions:
        for entry in decisions:
            ensure(3)
            page.line(f"{entry.t_label} | {entry.actor} | {entry.action}")
            if entry.rationale:
                page.line(f"Reason: {entry.rationale}", indent=10, size=8, color="0.35 0.39 0.44 rg")
    else:
        page.line("No decisions have been recorded.")

    ensure(5)
    page.heading("6. Liquidation reviews")
    reviews = summary.liquidation_reviews or []
    if reviews:
        for entry in reviews:
            ensure(3)
            page.line(f"{entry.t_label} | {entry.actor} | {entry.action} | verdict: {entry.liquidation_review}")
            if entry.rationale:
                page.line(f"Reason: {entry.rationale}", indent=10, size=8, color="0.35 0.39 0.44 rg")
    else:
        page.line("No liquidation reviews have been recorded.")

    ensure(5)
    page.heading("7. Communication actions")
    if summary.comms:
        for entry in summary.comms:
            ensure(2)
            page.line(f"{entry.t_label} | {entry.actor} | {entry.action}")
    else:
        page.line("No communications have been approved or sent.")

    ensure(5)
    page.heading("8. Incident timeline")
    # The full journal retains every alert for audit.  The report timeline
    # stays readable by including state changes, human decisions and only
    # critical alerts (rather than a page of repeated warning emissions).
    timeline = [
        entry for entry in session.journal.entries
        if entry.type in {"transition", "decision", "comm"}
        or (entry.type == "alert" and "critical" in entry.action.lower())
    ]
    if timeline:
        for entry in timeline:
            ensure(2)
            page.line(f"{entry.t_label} | {entry.actor} | {entry.action}")
    else:
        page.line("No incident events have been recorded.")

    ensure(4)
    page.heading("9. Final status")
    page.line(f"Current modelled status: {command.risk_level} ({session.machine.state if session.started else 'IDLE'})")
    page.line("Open items: " + ("; ".join(summary.open_items) if summary.open_items else "None recorded."))
    page.line("This report is an auditable simulation artifact. It does not assert real customer positions, exchange faults or guaranteed market outcomes.", size=8, color="0.38 0.12 0.12 rg")

    ensure(4)
    page.heading("10. Assumptions")
    for assumption in _ASSUMPTIONS:
        ensure(3)
        page.line(f"- {assumption}")
    return _build_pdf(pages)
