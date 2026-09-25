import type { ScenarioSummary } from '../types'

export function ScenarioPicker({ scenarios, value, onChange, disabled }: { scenarios: ScenarioSummary[]; value: string; onChange: (id: string) => void; disabled?: boolean }) {
  return <label className="flex items-center gap-2 text-xs text-white/75">Scenario
    <select className="max-w-44 border border-white/30 bg-slate-900 px-2 py-1.5 text-white" value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
      <option value="C1">C1 · Black Tuesday</option>
      {scenarios.filter((scenario) => scenario.id !== 'C1').map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.id} · {scenario.name}</option>)}
    </select>
  </label>
}
