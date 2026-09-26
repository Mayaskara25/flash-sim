# H12: Layout shell, details drawer, compact banner

| | |
|---|---|
| Branch | `h12-layout` (from `main` after H11 is merged) |
| Size | M |
| Depends on | H11 |
| Parallel with | H13 |
| Blocks | H14, H15 |

## Goal
Restructure the console into the target layout in `docs/UI_PLAN.md` §2: a compact banner, **three main columns** (Key signals · Do now · Timeline) and a **details drawer** with tabs. Everything must fit 1280×720 without scrolling. This handoff moves panels into their new places; it doesn't redesign their insides (that's H14).

## Read first
`docs/UI_PLAN.md` (all), `docs/PLAN.md` §2 and §4, `frontend/src/incident/IncidentConsole.tsx`, `SeverityBanner.tsx`, `ForecastStrip.tsx`, `RiskBrief.tsx`.

## You own
`frontend/src/incident/IncidentConsole.tsx`, new `frontend/src/incident/layout/DetailsDrawer.tsx`, new `frontend/src/incident/layout/MainColumns.tsx`, `components/SeverityBanner.tsx`, `components/ForecastStrip.tsx`. You may *delete the render* of RiskBrief from the console, but leave its file for H14 to remove.

## Tasks
- [ ] **Banner**, 3 rows and ≤ 150px tall:
  - Row 1: SEV + state + timer + scenario + tag chips + clock controls.
  - Row 2: a one-line brief built from `command.headline` (or RiskBrief's text) + classifier verdict.
  - Row 3: forecast headline + a "🔊 Brief me" button (calls the existing copilot "Brief me" logic; H15 will polish it) + a "Details ▸" button.
- [ ] **Main columns** (CSS grid, `minmax` widths, no horizontal scroll at 1280px; stacks under 1024px):
  - Left: the existing `SignalGrid` limited to 4 tiles + "+N more" link.
  - Centre: ActionList (pass the current role) + the reminders line + a "N drafts waiting" link to Details › Comms.
  - Right: IncidentTimeline + TeamStatus under it.
- [ ] **DetailsDrawer:** right-side slide-over (~45% width, Esc closes, focus trapped, remembers the last tab in `localStorage` inside try/catch). Tabs: **Signals** (full SignalGrid + FundRunwayChart), **Liquidations** (LiquidationInvestigator), **Comms** (TemplatePanel), **Log** (IncidentLog), **Report** (IncidentReport/SummaryView). Deep links: `?details=comms` etc. Keyboard: `D` toggles the drawer.
- [ ] Remove from the main view: P2ActionQueue, TemplatePanel, IncidentLog, LiquidationInvestigator, AICopilot's big panel (H15 re-adds it as a dock; until then, put it in a temporary "Copilot" drawer tab).
- [ ] If the investigator has flagged fills, show a badge `⚑ 3 fills to review` in the banner that opens Details › Liquidations.

## Acceptance criteria
- At 1280×720 in C1 at T+14: no page scroll. Banner, 4 signal tiles, the hero action with its what-if, and the timeline are all visible.
- Every feature from before is reachable within 1 click (drawer tab or link). Nothing is lost.
- `npm run build` and `npm run lint` are green. Screenshots at T+0, T+14 and RESOLVED attached to the PR.
