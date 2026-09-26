# H14: Panel consolidation, readability and naming fixes

| | |
|---|---|
| Branch | `h14-panels` (from `main` after H12 and H13 are merged) |
| Size | L |
| Depends on | H12, H13 |
| Parallel with | H15 |

## Goal
Apply `docs/UI_PLAN.md` §3 to each panel: merge the duplicates, rebuild panels on the H13 primitives and type scale, and fix confusing names. After this, no text is under 12px and each fact has exactly one home.

## Read first
`docs/UI_PLAN.md` (all), H12 and H13 PRs, `backend/incident/command.py` (which fields feed `ActionQueueItem`, `TeamMember`, `CommandBrief`).

## You own
`components/{SignalCard,SignalGrid,ActionList,ActionCard,P2ActionQueue,TemplatePanel,IncidentTimeline,IncidentLog,TeamStatus,RoleSwitcher,LiquidationInvestigator,TagChips,RiskBrief,WhatIfBadge,FundRunwayChart}.tsx`, `roleFocus.ts`, `useIncident.ts` (only if needed for data plumbing).

## Tasks
- [ ] **Actions: one list.**
  - Merge P2ActionQueue into ActionList. Order by band (NOW → NEXT → MONITOR), then priority.
  - Render the top one for the role as a **hero card**: large title, rationale hint, what-if as `68% → 21%` in a large font, and a large Approve button.
  - Show the next 2 as compact rows (text + role + small Approve), then "+N queued" (expandable).
  - Delete `P2ActionQueue.tsx` and its import.
  - Put these first in the hero slot: actions with a `control_id` and a what-if, and pending IC confirmations. Generic "acknowledge" items rank below them unless nothing is acknowledged yet.
- [ ] **Signals:**
  - Tiles use `Stat`: value ≥ 28px, a status badge in words, a trend arrow, and a sparkline with threshold lines.
  - The main view shows 4 tiles (worst first). "+N more · all normal" (or "· 2 watch") opens Details › Signals.
  - The full grid in the drawer uses the same tile at a smaller size.
- [ ] **Timeline:**
  - IncidentTimeline shows the last 6 key events (transitions, decisions, comms, first alert per signal) with **role names IC/TL/CS**. Remove the `IC→P1, TL→P2, CS→P3` mapping.
  - IncidentLog (drawer) stays the full, filterable audit log.
- [ ] **Team:** replace the TeamStatus panel with status dots and names inside RoleSwitcher (`IC ● Busy`). Delete the panel render.
- [ ] **RiskBrief:** delete the component. Its text lives in the banner (H12). Make sure nothing else imports it.
- [ ] **Comms:** TemplatePanel lives in Details › Comms. Keep a compact "N drafts waiting" link in the centre column (H12 added the link; make the count correct).
- [ ] **LiquidationInvestigator:** restyle for the drawer. Flagged fills first, each with "modelled threshold vs fill, delay", and decision buttons that write to the log.
- [ ] **Tags:** chips show `M2 · Insurance fund drain` (short name via `tagName`), with a tooltip for the full name.
- [ ] **Naming:** the UI says "MochaTrade Ops Console"; drop "P2" as a product name in UI strings (keep the backend module names). Roles are IC/TL/CS everywhere.
- [ ] Sweep: no `text-[10px]` or `text-[11px]` left in `frontend/src/incident/**`. Use the H13 tokens.

## Acceptance criteria
- `grep -rE "text-\[(9|10|11)px\]" frontend/src/incident` returns nothing.
- `grep -rn "P1'\|'P2'\|'P3'" frontend/src/incident/components` finds no role labels.
- At C1 T+14 the hero action is **reduce-only**, with its what-if visible and no scrolling.
- Build and lint green; before/after screenshots at T+14 in the PR.

## Findings from the H12+H13 review (screenshots of C1 at T+14, 1280×720): fix these here
1. **The hero action isn't visible.** "Do now" leads with *Acknowledge* and *Declare SEV-1*, and **reduce-only is below the fold**. Apply the hero-ranking rule above, and use compact rows for items 2–3 so the column fits without scrolling.
2. **Default role is "All",** which shows every role's cards. Default to **IC**, and make "All" show at most 1 hero plus 2 rows per role.
3. **The misleading banner brief** at T+14 says "Investigate liquidation cluster LC-07 — Next: Review 8 flagged executions" while the classifier says MARKET (LAR 1.0). In a market-driven phase the brief must lead with the protective control (reduce-only) and the fund. Treat the flagged fills as a secondary badge only. The source is `backend/incident/command.py` (headline and next-step logic): H14 may edit its wording/priority, keeping the endpoint shape.
4. **Timeline** shows only `SYS … alert` lines. Show transitions, decisions and comms first, plus the *first* alert per signal, and use signal labels ("Liquidation rate critical") rather than codes.
5. **Team status** still says P1/P2/P3 (as expected; covered above).
6. **Drawer › Signals:** the "SEV-1 ≤15m: 100%" text is yellow on white, which has too little contrast. Use the H13 severity tokens.
7. **Banner:** the controls wrap onto a second row. Move Scenario/Speed/Reset into one compact group (or an overflow menu) so the banner stays ≤ 150px. Drop the separate "MOCHATRADE / OPERATIONS" top bar (≈55px), because the banner can carry the product name.
8. The fixed "?" help button overlaps panel content at the bottom right. Anchor it inside the banner instead.
9. H12 lightly touched `IncidentTimeline.tsx` and `SignalGrid.tsx` (owned here). Build on those changes rather than reverting them.
