# H16: UI acceptance (projector, 3-second test, rehearsal)

| | |
|---|---|
| Branch | `h16-ui-acceptance` |
| Size | S |
| Depends on | H12–H15 merged |
| Owner | A + B together |

## Tasks
- [ ] **Projector check:** run at 1280×720 (and the real projector if possible). Read everything from 4 m away in light and dark mode. List anything unreadable and fix it.
- [ ] **3-second test** with 2 people who haven't seen the app: show C1 at T+14 for 3 seconds, hide it, and ask four questions:
  1. How bad is it?
  2. What's causing it?
  3. What should happen next?
  4. Who does it?

  Record the answers in the PR. Pass = both get all 4.
- [ ] **No-scroll check:** at T+0, T+14, T+24 (no-action branch) and RESOLVED, nothing important is below the fold.
- [ ] **Keyboard pass:** `1/2/3/0` roles, `A`/`S` hero action, `D` drawer, `Space` pause, `?` help. The shortcut overlay is up to date.
- [ ] **Update `docs/DEMO.md`** for the new layout: where to click, when to say "Brief me", when to open the drawer (Liquidations for C3), and the closed screen + PDF at the end.
- [ ] **Two full rehearsals** of C1 at 8× plus one C3 run. Fix whatever breaks, then tag `demo-v2`.

## Acceptance criteria
3-second test passed; two clean rehearsals; `demo-v2` tag pushed.
