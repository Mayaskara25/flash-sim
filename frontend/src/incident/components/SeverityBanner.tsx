import { severityTone } from '../format'
import type { IncidentActions } from '../useIncident'
import type { IncidentStateDTO, ScenarioSummary } from '../types'
import { AssumptionsPanel } from './AssumptionsPanel'
import { ForecastStrip } from './ForecastStrip'
import { SimClockControls } from './SimClockControls'
import { TagChips } from './TagChips'
import type { DetailsTab } from '../layout/detailsTabs'

/**
 * H14: the banner is the only coloured surface on the screen (UI_PLAN rule 5)
 * and stays at or under 150px. Row 1 is status, row 2 the one-line brief,
 * row 3 the forecast plus "Brief me" and "Details".
 *
 * Scenario / speed / reset live in one compact control group, and the help
 * button is anchored here rather than floating over the panels (H12/H13
 * review findings 7 and 8).
 */
export function SeverityBanner({ state, scenarios, actions, busy, mock, stale, briefLine, flaggedFills, briefing, onBriefMe, onOpenDetails, onHelp }: {
  state: IncidentStateDTO
  scenarios: ScenarioSummary[]
  actions: IncidentActions
  busy: boolean
  mock: boolean
  stale: boolean
  briefLine: string | null
  flaggedFills: number
  briefing: boolean
  onBriefMe: () => void
  onOpenDetails: (tab?: DetailsTab) => void
  onHelp: () => void
}) {
  const { severity, sim } = state
  const fund = state.signals.find((signal) => signal.code === 'INS_FUND_PCT')
  return <section className={`max-h-[150px] shrink-0 overflow-hidden border-b-4 px-4 py-1.5 md:px-6 ${severityTone[severity.sev] ?? severityTone[4]}`} aria-label="Incident status">
    <div className="flex flex-nowrap items-center gap-x-2.5 gap-y-1 overflow-hidden">
      <span className="whitespace-nowrap text-xl font-bold tracking-tight">SEV-{severity.sev} · {severity.state}</span>
      <span className="whitespace-nowrap font-mono text-sm tabular">{sim.t_label}</span>
      <span className="hidden text-xs whitespace-nowrap opacity-75 xl:inline">{sim.scenario_name ?? 'No incident running'}</span>
      <span className="hidden md:inline"><TagChips tags={state.tags} /></span>
      {/* The verdict and LAR are already the first words of the brief line
          below, so they are not repeated here (UI_PLAN rule 6). */}
      {flaggedFills > 0 && <button type="button" onClick={() => onOpenDetails('liquidations')} className="whitespace-nowrap text-xs font-bold border border-amber-200 px-1.5 py-0.5" style={{ background: '#fbbf24', color: '#1f2937' }}>⚑ {flaggedFills} fills</button>}
      <span className="ml-auto flex shrink-0 items-center gap-1.5">
        {mock && <span className="text-xs border border-white/35 px-1.5 py-0.5">SAMPLE</span>}
        {stale && <span className="text-xs border px-1.5 py-0.5" style={{ borderColor: '#fbbf24', background: '#fbbf24', color: '#1f2937' }}>STALE</span>}
        <AssumptionsPanel />
        <button type="button" onClick={onHelp} aria-label="Keyboard shortcuts" className="text-xs font-bold border border-white/35 px-1.5 py-0.5 hover:bg-card/10">?</button>
        <SimClockControls state={state} scenarios={scenarios} actions={actions} busy={busy} />
      </span>
    </div>
    {briefLine && <p className="mt-0.5 truncate text-body leading-snug" style={{ color: '#fff' }} title={briefLine}>{briefLine}</p>}
    {severity.overrides.length > 0 && <p className="truncate text-xs" style={{ color: 'rgba(255,255,255,0.75)' }}>Override: {severity.overrides.join(', ')}</p>}
    <div className="mt-1 flex items-center gap-2">
      <div className="min-w-0 flex-1"><ForecastStrip forecast={state.forecast} fund={fund} t={sim.t} compact /></div>
      <button type="button" disabled={briefing} onClick={onBriefMe} className="text-body shrink-0 border border-white/40 px-2 py-1 font-semibold hover:bg-card/10 disabled:opacity-50" style={{ color: '#fff' }}>{briefing ? 'Briefing…' : '🔊 Brief me'}</button>
      <button type="button" onClick={() => onOpenDetails()} className="text-body shrink-0 border border-white px-2 py-1 font-semibold" style={{ background: '#fff', color: '#0f172a' }}>Details ▸</button>
    </div>
  </section>
}
