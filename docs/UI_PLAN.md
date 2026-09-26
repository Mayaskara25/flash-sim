# UI Plan: make the console calm, legible and obvious

> Companion to `docs/PLAN.md`. The judges score "speed and clarity under a live scenario" and "reduces chaos rather than adding another screen to watch". After H11 the console has ~13 panels and mostly 10–11px text. This plan brings it back to one calm screen, with details a click away.

## 1. Design rules (every UI handoff is checked against these)

1. **The 3-second test.** At 1280×720 with no scrolling, a stranger can say: how bad it is, what's causing it, what to do next, and who does it.
2. **One primary action on screen.** The current role's top action is the biggest button. At most 2 more are visible; everything else sits behind "+N queued".
3. **Five things on screen, not 13.** The main view has: banner, key signals, do-now, timeline, and a copilot button. Everything else goes in a **details drawer** with tabs.
4. **Type scale for a projector.** Body ≥ 14px, labels ≥ 12px, key numbers ≥ 28px, severity headline ≥ 32px. No 10px text.
5. **Colour means severity.** Red, orange and amber appear only on the banner and on items at warn/critical. Everything else is neutral. No colour-only meaning: always add text or an icon.
6. **No duplicates.** Each fact has one home. If it shows in the banner, it doesn't get its own panel.
7. **Calm motion.** Only a newly crossed signal pulses (5 s). No auto-scroll. Nothing blinks.
8. **Plain words.** Roles are IC/TL/CS everywhere. Scenario tags carry a short name on hover, e.g. `M2 · Insurance fund drain`. No "P1/P2/P3" for people.

## 2. Target layout (1280×720)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ SEV-2 CRITICAL  T+14:32  Black Tuesday   [M1 Crash][M2 Fund drain][I1 Tickets]  ▶ 8× ⏸   │  ← banner ≤ 150px
│ Market-driven (LAR 1.1). Fund 40% and falling 4%/min.                                     │     one-line brief (was RiskBrief)
│ ⚠ Forecast: SEV-1 in ~9 min (68%) unless reduce-only          [🔊 Brief me]  [Details ▸]   │     forecast strip + voice
├──────────────────────────────┬──────────────────────────────────┬────────────────────────┤
│ KEY SIGNALS (4 big tiles)    │ DO NOW · IC   (IC TL CS All)      │ TIMELINE (last 6)      │
│ LIQ RATE   410/min  CRIT     │ ┌──────────────────────────────┐ │ 14:32 → CRITICAL       │
│ INS FUND   40%      WARN     │ │ Switch to reduce-only         │ │ 14:30 CS sent T1       │
│ PRICE 5m  −9.8%     WARN     │ │ P(SEV-1) 68% → 21%            │ │ 06:10 I1 tickets 4×    │
│ TICKETS    4.3×     WARN     │ │ [ Approve ]   Skip            │ │ 00:28 → WARNING        │
│ +17 more · all normal        │ └──────────────────────────────┘ │ Full log in Details ▸  │
│                              │ Next: T3 notice (CS) · Page TL    │                        │
│                              │ 2 drafts waiting · +6 queued      │ Team: IC ● TL ● CS ●   │
└──────────────────────────────┴──────────────────────────────────┴────────────────────────┘
 Details drawer (right side, ~45% width) · tabs: Signals · Liquidations · Comms · Log · Report
 Copilot: floating button bottom-right → opens a panel (Ask / Brief me / voice)
```

## 3. Panel inventory: what happens to each

| Current panel | Decision | New home |
|---|---|---|
| SeverityBanner | **Keep, compact** | Banner row 1 |
| ForecastStrip | **Keep** | Banner row 3; runway chart moves to Details › Signals |
| RiskBrief | **Merge** into the banner as the one-line brief | Banner row 2 |
| SignalGrid / SignalCard | **Keep 4 big tiles**; the rest collapse into a single "+N more" line | Main, left column; the full grid moves to Details › Signals |
| ActionList / ActionCard | **Keep**: one hero card plus 2 compact "next" rows | Main, centre |
| P2ActionQueue | **Merge** into ActionList. Its NOW/NEXT/MONITOR bands become the ordering; no second list | — |
| TemplatePanel | **Move.** Show a "2 drafts waiting" badge in the centre column; the full editor goes to Details › Comms | Details |
| IncidentTimeline | **Keep** (last 6 key events) | Main, right column |
| IncidentLog | **Move** (full, filterable) | Details › Log |
| TeamStatus | **Shrink** to 3 status dots on the role switcher | Role switcher |
| LiquidationInvestigator | **Move**; badge in the banner if any fills are flagged | Details › Liquidations |
| AICopilot | **Move** to a floating dock; keep "Brief me" in the banner | Dock |
| IncidentReport / SummaryView | **Keep**; a full-screen "Incident closed" view appears on RESOLVED with Download PDF | Details › Report + end screen |
| AssumptionsPanel | Keep (slide-over from the SIMULATION badge) | unchanged |
| Reminders ("update overdue") | Keep as one amber line in the centre column | Main |

## 4. Handoffs and order

```
H11 merge (done, needs PR) ──▶ H12 Layout & hierarchy ──┬──▶ H14 Panel consolidation ──┐
                           └─▶ H13 Design tokens (∥ H12) ─┘                             ├──▶ H16 UI acceptance
                                                      H12 ──▶ H15 Voice & report UX ────┘
```

| ID | Title | Depends on | Parallel with | Owns (main files) |
|---|---|---|---|---|
| H12 | Layout shell, details drawer, banner | H11 | H13 | `IncidentConsole.tsx`, new `layout/DetailsDrawer.tsx`, `SeverityBanner.tsx`, `ForecastStrip.tsx` |
| H13 | Design tokens, type scale, UI primitives | H11 | H12 | `index.css`, new `ui/*` (Panel, Stat, Badge, Button, Tag), `format.ts` |
| H14 | Panel consolidation + naming fixes | H12, H13 | H15 | Signal*, Action*, P2ActionQueue, Template*, IncidentTimeline, IncidentLog, TeamStatus, RoleSwitcher, LiquidationInvestigator, TagChips, `roleFocus.ts` |
| H15 | Voice copilot dock + end-of-incident report UX | H12 | H14 | `AICopilot.tsx`, `IncidentReport.tsx`, `SummaryView.tsx`, `IncidentSummaryPage.tsx`, `backend/incident/report.py`, `copilot.py` (wording only) |
| H16 | UI acceptance: projector, 3-second test, rehearsal | all | — | `docs/DEMO.md`, screenshots |

Two-person split: **A:** H11 → H12 → H15. **B:** H13 → H14. **Together:** H16.
