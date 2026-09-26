# H15: Voice copilot dock and end-of-incident report

| | |
|---|---|
| Branch | `h15-voice-report` (from `main` after H12) |
| Size | M |
| Depends on | H12 |
| Parallel with | H14 |

## Goal
Turn the copilot and report from "panels on the page" into two moments that are good in a demo:
1. A **voice briefing** that stays out of the way until asked, and can optionally announce escalations.
2. A clean **"Incident closed" screen** on RESOLVED, with the PDF report one click away.

## Read first
`docs/UI_PLAN.md`, H11 handoff, `frontend/src/incident/components/{AICopilot,IncidentReport,SummaryView}.tsx`, `IncidentSummaryPage.tsx`, `backend/incident/{copilot,report,command}.py`.

## You own
`components/AICopilot.tsx` (→ `CopilotDock.tsx`), `components/IncidentReport.tsx`, `components/SummaryView.tsx`, `IncidentSummaryPage.tsx`, new `components/IncidentClosed.tsx`, `backend/incident/report.py`, and `backend/incident/copilot.py` (wording and answer quality only; keep the endpoint shape).

## Tasks
- [ ] **Copilot dock:**
  - A floating button bottom-right ("Ask copilot") opens a ~400px panel with the question box, voice "Ask", "Brief me" and the last answer (First priority / Why / Next).
  - Esc closes it. It never covers the hero Approve button: the panel sits above the dock and doesn't overlap the centre column at 1280px.
- [ ] **Voice:**
  - One shared `speak()` util: cancels the previous utterance, picks an English voice if one is available, rate 1.05.
  - Hide the voice "Ask" button if speech recognition is missing (Firefox). Show a tooltip rather than an error.
  - **Announce escalations** (toggle in the dock, default **off**): on an upward transition, speak one line, e.g. "Severity 2, critical. Liquidations 410 per minute. Recommended: reduce-only." Never speak more than once per 20 s.
  - The banner's "🔊 Brief me" (H12) uses the same util.
- [ ] **Copilot answers:** check the 3 demo questions ("What should I do first?", "What changed in the last 5 minutes?", "Why was this flagged?") give short, correct answers at T+0, T+14 and T+40 of C1. Keep answers to 2–3 sentences; every number must come from state.
- [ ] **Incident closed screen:**
  - On `RESOLVED`, or `t ≥ duration`, show a full-width card over the main view: duration, peak SEV, peak signals, decisions count, comms count, liquidation review verdicts, open items.
  - Buttons: **Download PDF report** (`/api/incident/report.pdf`), **View timeline**, **Copy summary (Markdown)**, **Back to console**.
- [ ] **PDF report:**
  - Check `report.py` output: title page with scenario, times and peak SEV; the timeline table; the decisions with who/why; comms sent (full text); liquidation reviews; the assumptions page.
  - Watch the ASCII-only encoding: `→`, `≤` and `₹` are silently dropped today. Replace them with ASCII (`->`, `<=`, `INR`) before encoding.
  - Add a test asserting the PDF starts with `%PDF` and contains the scenario name and at least one decision.

## Acceptance criteria
- Voice works in Chrome and degrades quietly in Firefox.
- Escalation announcements are off by default; when on, at most 1 per 20 s.
- The C1 run to RESOLVED shows the closed screen, and the PDF downloads with no missing characters.
- `pytest -q`, build and lint green.
