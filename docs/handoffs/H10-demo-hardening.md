# H10: Demo hardening and freeze

| | |
|---|---|
| Branch | `h10-demo` |
| Owner | A + B together |
| Size | S |
| Depends on | all |

## Goal
Make the live demo boring (in a good way): rehearsed, timed, reproducible, and visibly grounded in the Round 1 plan.

## Tasks
- [ ] **Demo script:** `docs/DEMO.md`, adapted from SPEC §12.2, with exact clicks, who speaks, the target sim time for each beat, and the fallback if something breaks (debug jump buttons, reload, `POST /incident/reset`). Include the "with vs without reduce-only" moment using the what-if badge and the no-action branch.
- [ ] **Round 1 grounding:** one line per playbook in the Assumptions panel or the README, mapping it back to our Round 1 recommendation (fill in from the Round 1 deck).
- [ ] **Analyst sync (nice to have):** while an incident runs, push the incident's current price move into `ENGINE.update(crash_magnitude=...)` (throttled to once per 5 sim-s) so the `/analyst/*` drill-downs match the console. Owned file: `backend/incident/session.py` (small hook) — coordinate.
- [ ] **README:** new top section "Flash-Crash Console" with run instructions (`./start.sh` / `start.ps1`), a screenshot, the architecture diagram from PLAN §4, and the assumptions.
- [ ] **Brief checklist:** walk through PLAN §2 tables and tick each item live.
- [ ] **Rehearsals:** 2 full C1 runs at 8× within 8–9 min each, plus one C3 run (the classifier story). Log issues and fix them.
- [ ] **Freeze:** tag `demo-v1` on `main`, and test it on the actual demo laptop and projector resolution.

## Acceptance criteria
Two consecutive clean rehearsals; the tag is pushed; the demo laptop has everything installed offline (no `npm install` on stage).
