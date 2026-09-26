import { useEffect, useState } from 'react'
import { Panel } from '../components/KpiCard'
import { useSim } from '../context/SimContext'
import { api } from '../services/api'
import { inrFromUsd, num, statusBg } from '../services/format'
import type { Cascade } from '../types'

export function CascadeRiskPage() {
  const { revision, overview } = useSim()
  const [c, setC] = useState<Cascade | null>(null)
  const [sel, setSel] = useState<string | null>(null)
  useEffect(() => {
    void api.cascade().then((r) => {
      setC(r)
      setSel((s) => s ?? r.stages[0]?.id)
    })
  }, [revision])
  if (!c) return <p className="text-sm text-muted">Loading cascade model…</p>
  const fx = overview?.market.usd_inr ?? 83.5
  const stage = c.stages.find((s) => s.id === sel) ?? c.stages[0]
  const tone = c.classification === 'CRITICAL' || c.classification === 'HIGH' ? 'crit' : c.classification === 'MEDIUM' ? 'warn' : 'safe'
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">AI Cascade Risk</h1>
        <p className="max-w-3xl text-[13px] text-muted">
          The model estimates whether current simulated conditions resemble setups associated with a potential liquidation
          cascade. It is not a prediction of future prices.
        </p>
        <p className="mt-1 text-[11px] text-muted">{c.model_note}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="CASCADE RISK SCORE">
          <div className={`text-4xl tabular ${tone === 'crit' ? 'text-crit' : tone === 'warn' ? 'text-warn' : 'text-safe'}`}>
            {c.cascade_risk_score} / 100
          </div>
          <div className={`mt-2 inline-block px-2 py-0.5 text-[12px] ${statusBg(c.classification)}`}>{c.classification}</div>
          <div className="mt-3 h-2 w-full bg-[#eef0f2]">
            <div
              className={`h-2 ${tone === 'crit' ? 'bg-crit' : tone === 'warn' ? 'bg-warn' : 'bg-safe'}`}
              style={{ width: `${c.cascade_risk_score}%` }}
            />
          </div>
        </Panel>
        <Panel title="FEATURE STATES">
          <dl className="grid grid-cols-1 gap-1 text-[13px]">
            {Object.entries(c.features).map(([k, v]) => (
              <div key={k} className="flex justify-between border-b border-line py-1">
                <dt className="text-muted">{k}</dt>
                <dd className={v === 'High' || (v === 'Low' && k === 'Liquidity') ? 'text-crit' : ''}>{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel title="WHY IS CASCADE RISK ELEVATED?">
          <p className="text-[13px] leading-relaxed">{c.why}</p>
        </Panel>
      </div>
      <Panel title="CASCADE FLOW" footnote="Click a stage for counts, exposure and risk contribution. No forecast is implied.">
        <div className="flex flex-col gap-0">
          {c.stages.map((s, i) => (
            <div key={s.id}>
              <button
                type="button"
                onClick={() => setSel(s.id)}
                className={`w-full border px-3 py-2 text-left text-[12px] ${
                  sel === s.id ? 'border-navy bg-[#f3f4f6]' : 'border-line bg-white'
                }`}
              >
                {s.title}
              </button>
              {i < c.stages.length - 1 && <div className="py-1 text-center text-[11px] text-muted">↓</div>}
            </div>
          ))}
        </div>
        {stage && (
          <div className="mt-4 grid grid-cols-3 gap-3 border border-line bg-[#fafafa] p-3 text-[13px]">
            <div>
              <div className="text-[10px] text-muted">Positions</div>
              <div className="tabular font-medium">{num(stage.positions)}</div>
            </div>
            <div>
              <div className="text-[10px] text-muted">Exposure</div>
              <div className="tabular font-medium">{inrFromUsd(stage.exposure_usd, fx)}</div>
            </div>
            <div>
              <div className="text-[10px] text-muted">Risk contribution</div>
              <div className="tabular font-medium">{stage.risk_contribution.toFixed(1)}</div>
            </div>
            <p className="col-span-3 text-[12px] text-muted">{stage.detail}</p>
          </div>
        )}
      </Panel>
    </div>
  )
}
