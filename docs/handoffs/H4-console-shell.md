# H4: Frontend console shell on fixtures

| | |
|---|---|
| Branch | `h4-console-shell` |
| Owner | B (teammate) |
| Size | L |
| Depends on | H0 |
| Blocks | H6 |

## Goal
Build the one-screen incident console (PLAN §4 "Screen") as React components that render any `IncidentStateDTO`, driven by the H0 fixtures. No live backend is needed. Also restructure routing so the console is the landing page and the old pages become analyst drill-downs.

## Read first
PLAN §2–4 · CONTRACTS §5–6 · SPEC §9.5, §10 ("anti-chaos rules"), §12.2 · existing `frontend/src/components/*`, `frontend/src/index.css` (colour tokens), `frontend/src/services/format.ts`

## You own
- `frontend/src/incident/components/*` (new): `SeverityBanner.tsx`, `SignalCard.tsx`, `SignalGrid.tsx`, `ActionList.tsx`, `ActionCard.tsx`, `TemplatePanel.tsx`, `IncidentLog.tsx`, `RoleSwitcher.tsx`, `SimClockControls.tsx`, `ScenarioPicker.tsx`, `TagChips.tsx`
- `frontend/src/incident/IncidentConsole.tsx`, `frontend/src/incident/useIncident.ts` (fixture mode only in H4), `frontend/src/incident/format.ts`
- `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx` (routing/nav only)

## Design
- **Zone ① Severity banner** (full width, sticky): colour by SEV (SEV-1 red, SEV-2 orange, SEV-3 amber, SEV-4 neutral), state name, `t_label` sim timer, tag chips (active solid, inactive outlined), classifier verdict + LAR + one-line explanation, active overrides as red pills, and a placeholder slot for the forecast headline (H9 fills it). Right side: scenario picker, speed buttons (1×/5×/8×/10×), pause/resume, reset.
- **Zone ② Signals:** `relevant` signals as cards (max 6 expanded, ordered by status then relevance), each with value + unit, status colour, trend arrow, a Recharts sparkline of `history` with warn/critical reference lines, and an alert counter badge from `alerts`. Remaining signals go in a collapsed "+N more" row of compact chips. Each card links to the matching analyst page (LIQ_RATE → `/analyst/liquidations`, INS_FUND → `/analyst/exposure`, etc.).
- **Zone ③ Next actions:** a role switcher (All/IC/TL/CS; persist in `localStorage` inside try/catch). For each role, **max 3** proposed actions; then "+N queued". An action card shows role chip, text, tag, `rationale_hint`, an expiry countdown if time-boxed, a `what_if` badge slot (H9), and Approve / Skip buttons. Both open a small modal with a required rationale textarea pre-filled from `rationale_hint`. Below: surfaced **templates** (title, audience/channel chip, pre-filled text, `missing` placeholders highlighted, Edit → textarea, "Approve & send as <role>", Dismiss). A reminder strip shows `reminders[]`. A pending-confirmation card (`severity.pending`) appears at the top for IC.
- **Zone ④ Incident log:** newest first, type icons, filter chips by type, a `liquidation_review` pill, and expandable `signal_snapshot`. A "Mark liquidations: market-explained / under review / wrongful" control sits here (IC only).
- **Layout:** desktop/projector first (≥ 1280 px): banner on top; left column signals; right column actions over log. Must stay readable at 1024 px. High contrast, since it will be projected.
- **Routing:** `/` → `IncidentConsole`; existing pages move to `/analyst/overview`, `/analyst/market-crash`, `/analyst/liquidations`, `/analyst/cascade`, `/analyst/monte-carlo`, `/analyst/exposure`, `/analyst/risk-response`. Nav: "Incident Console" and an "Analyst" group. `SimControls` shows only on analyst pages.
- **Fixture mode:** `useIncident()` returns `{state, catalogue, actions: {...no-ops that advance the fixture}}`. With `VITE_INCIDENT_MOCK=1`, or when `?mock=1` is in the URL, it cycles fixtures via a dev-only "next fixture" button. Keep the hook's return type exactly what H6 will implement for real.

## Tasks
- [ ] Components above, typed against `frontend/src/incident/types.ts` only.
- [ ] Routing restructure; old pages still work under `/analyst/*`.
- [ ] Every fixture renders with no console errors; the SEV colours are visually distinct.
- [ ] Hook signature documented in a comment block at the top of `useIncident.ts`.

## Acceptance criteria
- `npm run build` and `npm run lint` green.
- A screenshot per fixture state attached to the PR.
- A 3-second glance test: someone who hasn't seen it can say the severity, what's wrong, and what the IC should do next.

## Out of scope
Real polling and POSTs (H6), forecast UI (H9).
