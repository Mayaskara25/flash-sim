import { useEffect, useState } from 'react'
import { Panel } from '../components/KpiCard'
import { useSim } from '../context/SimContext'
import { api } from '../services/api'
import { pct, statusBg } from '../services/format'
import type { RiskSummary } from '../types'

export function RiskResponsePage() {
  const { revision } = useSim()
  const [r, setR] = useState<RiskSummary | null>(null)
  useEffect(() => {
    void api.risk().then(setR)
  }, [revision])
  if (!r) return <p className="text-sm text-muted">Loading risk summary…</p>
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">Risk Response</h1>
        <p className="max-w-3xl text-[13px] text-muted">
          Proposed monitoring actions for the research simulation. These are not live controls and are not claimed as
          production processes at any trading venue.
        </p>
      </div>
      <Panel title="CURRENT RISK LEVEL">
        <div className={`inline-block px-3 py-1 text-lg ${statusBg(r.current_risk_level)}`}>{r.current_risk_level}</div>
        <p className="mt-2 text-[12px] text-muted">Cascade indicator {r.cascade_score} / 100 · research prototype</p>
      </Panel>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="KEY REASONS">
          <ul className="list-disc space-y-1 pl-5 text-[13px]">
            {r.reasons.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <p className="mt-3 text-[12px] leading-relaxed text-muted">{r.why}</p>
          <p className="mt-2 text-[12px] text-muted">
            Monte Carlo severe-scenario frequency: {pct(r.severe_mc_frequency * 100, 1)} (simulation frequency under model
            assumptions).
          </p>
        </Panel>
        <Panel title="PROPOSED RISK RESPONSES" footnote="Proposed risk-management actions. Not implemented production controls.">
          <ol className="list-decimal space-y-1 pl-5 text-[13px]">
            {r.proposed_actions.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ol>
        </Panel>
      </div>
      <Panel title="DEMO NARRATIVE">
        <p className="text-[13px] leading-relaxed text-muted">
          P2 adds a predictive risk layer to leveraged trading by identifying vulnerable positions, detecting liquidation
          clusters, estimating cascade risk, stress-testing crash scenarios and quantifying financial exposure before the
          situation becomes widespread.
        </p>
      </Panel>
    </div>
  )
}
