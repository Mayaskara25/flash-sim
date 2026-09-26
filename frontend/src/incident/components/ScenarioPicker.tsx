import type { ScenarioSummary } from '../types'

/**
 * H14: the scenario picker is a bare control in the banner's compact control
 * group. The "Scenario" label was a second word on an already-wrapped row
 * (H12/H13 review finding 7); the scenario name is in the `C1 · …` option
 * text, so the label was pure width.
 */
export function ScenarioPicker({ scenarios, value, onChange, disabled }: { scenarios: ScenarioSummary[]; value: string; onChange: (id: string) => void; disabled?: boolean }) {
  return <select aria-label="Scenario" className="max-w-40 border border-white/30 bg-slate-900 px-2 py-1.5 text-xs text-white" value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
    <option value="C1">C1 · Black Tuesday</option>
    {scenarios.filter((scenario) => scenario.id !== 'C1').map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.id} · {scenario.name}</option>)}
  </select>
}
