# Handoffs

Each file here is a self-contained work package. Give the file (plus `docs/PLAN.md`, `docs/CONTRACTS.md` and `docs/SPEC.md`) to a person or agent, and they should be able to finish it without asking anyone.

| ID | Title | Depends on | Branch | Owner |
|---|---|---|---|---|
| [H0](H0-foundation.md) | Foundation: contracts, stubs, fixtures, CI | — | `h0-foundation` | A |
| [H1](H1-signals.md) | Sim clock, scenarios, book-driven signals | H0 | `h1-signals` | A |
| [H2](H2-rules-engine.md) | Rules engine | H0 | `h2-rules` | A |
| [H3](H3-playbooks-templates.md) | Playbooks, controls, templates | H0 | `h3-playbooks` | B |
| [H4](H4-console-shell.md) | Frontend console on fixtures | H0 | `h4-console-shell` | B |
| [H5](H5-session-api.md) | Session, operator API, log, summary | H1 H2 H3 | `h5-session-api` | A |
| [H6](H6-frontend-live.md) | Frontend live wiring | H4 H5 | `h6-frontend-live` | B |
| [H7](H7-forecast.md) | Prediction layer | H5 | `h7-forecast` | A |
| [H8](H8-scenario-pack.md) | Scenarios C2–C6 + injects | H5 | `h8-scenarios` | A/B |
| [H9](H9-frontend-forecast-polish.md) | Forecast UI, summary, polish | H6 | `h9-frontend-polish` | B |
| [H10](H10-demo-hardening.md) | Demo hardening | all | `h10-demo` | A+B |
| [H11](H11-merge-p2-updates.md) | Merge P2 updates (voice copilot, investigator, PDF) | H10 | `h11-p2-updates` | A |
| [H12](H12-layout-shell.md) | UI: layout shell, details drawer, banner | H11 | `h12-layout` | A |
| [H13](H13-design-tokens.md) | UI: design tokens, type scale, primitives | H11 | `h13-tokens` | B |
| [H14](H14-panel-consolidation.md) | UI: panel consolidation + naming | H12 H13 | `h14-panels` | B |
| [H15](H15-voice-report-ux.md) | UI: voice dock + incident-closed report | H12 | `h15-voice-report` | A |
| [H16](H16-ui-acceptance.md) | UI acceptance + rehearsal | H12–H15 | `h16-ui-acceptance` | A+B |

Order and parallelism: see PLAN §5.2–5.3 (H0–H10) and `docs/UI_PLAN.md` §4 (H11–H16).

## Standard rules for every handoff

1. Branch from the latest `main`. Name the branch as in the table.
2. Only edit files listed under **You own**. Read anything.
3. Don't change the contract unless the handoff says so. If you must, follow PLAN §6.
4. Before opening the PR: `cd backend && pytest -q`, then `cd frontend && npm run build && npm run lint`.
5. Tick the acceptance criteria in the PR description.
6. After merging: run `graphify update .` if you use graphify locally.
