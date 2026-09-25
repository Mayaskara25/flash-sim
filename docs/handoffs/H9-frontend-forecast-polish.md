# H9: Frontend forecast, what-if, summary, assumptions, anti-chaos polish

| | |
|---|---|
| Branch | `h9-frontend-polish` |
| Owner | B (teammate) |
| Size | M |
| Depends on | H6. Use the H0 fixtures (they include `forecast`) until H7 merges. |
| Blocks | H10 |

## Goal
Make the prediction feature visible without adding a screen, add the end-of-incident summary, and enforce the spec's anti-chaos rules visually.

## Read first
CONTRACTS §5–7 · H7 "Goal" · SPEC §10 (anti-chaos rules), §12.2, §13.3

## You own
`frontend/src/incident/components/ForecastStrip.tsx`, `WhatIfBadge.tsx`, `FundRunwayChart.tsx`, `SummaryView.tsx`, `AssumptionsPanel.tsx`; edits to `SeverityBanner.tsx`, `ActionCard.tsx`, `IncidentConsole.tsx`; route `/summary`

## Tasks
- [ ] **ForecastStrip** (inside the severity banner, one line): `headline`, a mini stacked bar of `sev_probs` at 15 min, and "Fund → 25% in p50–p90 min". Colour by `prob_within_15`. Tooltip: drivers + `cascade_model_p` + the label. Hidden when `forecast` is null.
- [ ] **FundRunwayChart** (click the strip to expand, inline): INS_FUND history + p10/p50/p90 fan for the next 15 min, with a 25% threshold line (Recharts `Area` for the band).
- [ ] **WhatIfBadge** on action cards: `P(SEV-1 15m) 68% → 21%` in green/red by direction; tooltip shows the fund p50 delta and `text`.
- [ ] **SummaryView** (`/summary`, and a button on RESOLVED): timeline, peak signals, decisions table (who/when/why), comms sent (full text), liquidation reviews, open items, "Copy as Markdown" (uses `summary.markdown`).
- [ ] **AssumptionsPanel:** a slide-over listing SPEC §13.3 items plus "all thresholds are simulation values", reachable from the banner's SIMULATION badge. This is what we read out at the start of the demo.
- [ ] **Anti-chaos polish:**
  - Enforce ≤ 6 expanded signal cards and ≤ 3 actions per role (assert in dev).
  - A subtle pulse only on *newly* crossed signals, for 5 s.
  - No sound; no auto-scrolling log (show "N new" pill instead).
  - Runbook phase + role focus text (H3 `ROLE_FOCUS`, exposed via a small addition to the DTO or the catalogue; coordinate) under the role switcher.
- [ ] Projector check: readable from 4 m at 1280×720 and in both light and dark mode.

## Acceptance criteria
- On C1 at T+14, a viewer can see the forecast headline, the fund runway and the reduce-only what-if without clicking.
- The summary page after a C1 run matches the log (spot-check 3 entries).
- Build/lint green; screenshots in the PR.
