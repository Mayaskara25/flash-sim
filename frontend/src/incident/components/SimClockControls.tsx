import { useState } from 'react'
import type { IncidentActions } from '../useIncident'
import type { IncidentStateDTO, ScenarioSummary } from '../types'
import { ScenarioPicker } from './ScenarioPicker'

/**
 * H14: scenario, speed and reset are one compact group in the banner.
 *
 * They were separate labelled controls that pushed the banner onto a second
 * row (H12/H13 review finding 7). The group never wraps: the picker is
 * disabled once a run starts, and the speed buttons share one border.
 */
export function SimClockControls({ state, scenarios, actions, busy }: { state: IncidentStateDTO; scenarios: ScenarioSummary[]; actions: IncidentActions; busy: boolean }) {
  const [scenarioId, setScenarioId] = useState('C1')
  const debug = new URLSearchParams(window.location.search).get('debug') === '1'
  const base = 'border px-2 py-1 text-xs disabled:opacity-50'
  if (!state.sim.started) {
    return <div className="flex items-center gap-1">
      <ScenarioPicker scenarios={scenarios} value={scenarioId} onChange={setScenarioId} disabled={busy} />
      <button type="button" disabled={busy} onClick={() => void actions.start({ scenario_id: scenarioId, speed: 8 }).catch(() => {})}
        className={`${base} border-white bg-white font-semibold text-slate-900 hover:bg-slate-100`}>Start {scenarioId}</button>
    </div>
  }
  return <div className="flex items-center gap-1">
    <button type="button" disabled={busy} onClick={() => void actions.clock({ op: state.sim.running ? 'pause' : 'resume' }).catch(() => {})}
      className={`${base} border-white/40 font-semibold hover:bg-white/10`}>{state.sim.running ? '⏸' : '▶'}</button>
    <div className="flex" role="group" aria-label="Simulation speed">
      {[1, 5, 8, 10].map((speed) => <button type="button" key={speed} disabled={busy} aria-pressed={state.sim.speed === speed}
        onClick={() => void actions.clock({ op: 'speed', speed }).catch(() => {})}
        className={`${base} -ml-px border-white/25 first:ml-0 hover:bg-white/10 ${state.sim.speed === speed ? 'bg-white/25 font-bold' : ''}`}>{speed}×</button>)}
    </div>
    <button type="button" disabled={busy} onClick={() => void actions.reset().catch(() => {})} className={`${base} border-white/25 hover:bg-white/10`}>Reset</button>
    {debug && <div className="flex" role="group" aria-label="Debug time jumps">
      {[0, 6, 14, 35, 55].map((minute) => <button type="button" key={minute} disabled={busy} onClick={() => void actions.clock({ op: 'jump', t: minute * 60 }).catch(() => {})}
        className={`${base} -ml-px border-white/25 first:ml-0 hover:bg-white/10`}>T+{minute}</button>)}
    </div>}
    {state.sim.t < 0 && <span className="border border-white/50 px-2 py-1 text-xs font-bold">Starting in {Math.ceil(-state.sim.t)}…</span>}
  </div>
}
