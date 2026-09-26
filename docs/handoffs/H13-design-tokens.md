# H13: Design tokens, type scale, UI primitives

| | |
|---|---|
| Branch | `h13-tokens` (from `main` after H11) |
| Size | S–M |
| Depends on | H11 |
| Parallel with | H12 (no shared files) |
| Blocks | H14 |

## Goal
Create a small, projector-friendly design system that H14 applies to every panel: a type scale, severity colour tokens (light and dark), and 5 primitives. **Don't restyle existing panels here** (that's H14); only create the tokens and primitives, and demo them.

## Read first
`docs/UI_PLAN.md` §1 (rules 4, 5, 7), `frontend/src/index.css` (current tokens), `frontend/src/incident/format.ts`, and a few panels to see the repeated patterns (`SignalCard`, `ActionCard`, `TagChips`).

## You own
`frontend/src/index.css`, new `frontend/src/incident/ui/{Panel,Stat,Badge,Button,Tag}.tsx`, new `frontend/src/incident/ui/index.ts`, `frontend/src/incident/format.ts`, new dev-only route `/ui-kit` (a tiny page registered in `App.tsx`; that one line is the only edit to `App.tsx`).

## Tasks
- [ ] **Type scale** as Tailwind 4 theme tokens / utility classes: `text-label` 12px/600/uppercase tracking, `text-body` 14px, `text-body-lg` 16px, `text-stat` 28px mono, `text-headline` 32px bold. Document them at the top of `index.css`.
- [ ] **Colour tokens:**
  - Severity: `--sev1` red, `--sev2` orange, `--sev3` amber, `--sev4` neutral, each with `-bg`/`-fg`/`-border` variants.
  - Status: `--ok`, `--warn`, `--crit`.
  - Neutrals: `--ink`, `--muted`, `--line`, `--surface`.
  - Define them on `:root` and redefine for dark mode under `@media (prefers-color-scheme: dark)` and `[data-theme=dark]`.
  - Contrast ≥ 4.5:1 for text (check with any contrast checker; list the ratios in the PR).
- [ ] **Primitives** (typed props, no business logic):
  - `Panel` (title, optional action, body)
  - `Stat` (label, value, unit, status, trend)
  - `Badge` (status/severity tone + text, always text rather than colour alone)
  - `Button` (primary/secondary/ghost, sizes md/lg, loading state)
  - `Tag` (scenario tag code + short name, tooltip with the full name from the catalogue/playbook)
- [ ] `format.ts`: consistent number formatting (thousands separators, 1 dp for %, `T+MM:SS`), and a `tagName(tag)` helper (e.g. `M2 → "Insurance fund drain"`).
- [ ] `/ui-kit` page showing every primitive in every tone, in light and dark.

## Acceptance criteria
- No token or primitive uses text under 12px.
- `/ui-kit` looks right in light and dark mode and at 1280×720.
- Build and lint green; a screenshot of `/ui-kit` in the PR.
