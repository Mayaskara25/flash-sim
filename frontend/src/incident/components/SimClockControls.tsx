import { useState } from 'react'
import type { IncidentActions } from '../useIncident'
import type { IncidentStateDTO, ScenarioSummary } from '../types'
import { ScenarioPicker } from './ScenarioPicker'

export function SimClockControls({ state, scenarios, actions, busy }: { state: IncidentStateDTO; scenarios: ScenarioSummary[]; actions: IncidentActions; busy: boolean }) {
  const [scenarioId, setScenarioId] = useState('C1')
  const debug = new URLSearchParams(window.location.search).get('debug') === '1'
  return <div className="flex flex-wrap items-center gap-2">
    <ScenarioPicker scenarios={scenarios} value={scenarioId} onChange={setScenarioId} disabled={busy || state.sim.started} />
    {!state.sim.started ? <button type="button" disabled={busy} onClick={() => void actions.start({ scenario_id: scenarioId, speed: 8 }).catch(() => {})} className="border border-white bg-white px-3 py-1.5 text-xs font-semibold text-slate-900 hover:bg-slate-100 disabled:opacity-50">Start C1</button> : <>
      <button type="button" disabled={busy} onClick={() => void actions.clock({ op: state.sim.running ? 'pause' : 'resume' }).catch(() => {})} className="border border-white/40 px-3 py-1.5 text-xs font-semibold hover:bg-white/10 disabled:opacity-50">{state.sim.running ? 'Pause' : 'Resume'}</button>
      <div className="flex gap-0.5" role="group" aria-label="Simulation speed">{[1, 5, 8, 10].map((speed) => <button type="button" key={speed} disabled={busy} onClick={() => void actions.clock({ op: 'speed', speed }).catch(() => {})} className={`border px-2 py-1.5 text-xs ${state.sim.speed === speed ? 'border-white bg-white/20' : 'border-white/25 hover:bg-white/10'}`}>{speed}×</button>)}</div>
      <button type="button" disabled={busy} onClick={() => void actions.reset().catch(() => {})} className="border border-white/25 px-2 py-1.5 text-xs hover:bg-white/10">Reset</button>
      {debug && <div className="flex flex-wrap gap-0.5" role="group" aria-label="Debug time jumps">{[0, 6, 14, 35, 55].map((minute) => <button type="button" key={minute} disabled={busy} onClick={() => void actions.clock({ op: 'jump', t: minute * 60 }).catch(() => {})} className="border border-white/25 px-2 py-1 text-[10px] hover:bg-white/10">T+{minute}</button>)}</div>}
    </>}
    {state.sim.started && state.sim.t < 0 && <span className="border border-white/50 px-2 py-1 text-xs font-bold">Starting in {Math.ceil(-state.sim.t)}…</span>}
  </div>
}

