import { useEffect, useState } from 'react'
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { KpiCard, Panel } from '../components/KpiCard'
import { useSim } from '../context/SimContext'
import { api } from '../services/api'
import { inrFromUsd } from '../services/format'
import type { Exposure } from '../types'

export function ExposurePage() {
  const { revision } = useSim()
  const [e, setE] = useState<Exposure | null>(null)
  useEffect(() => {
    void api.exposure().then(setE)
  }, [revision])
  if (!e) return <p className="text-sm text-muted">Loading exposure…</p>
  const fx = e.usd_inr
  const lev = Object.entries(e.by_leverage).map(([k, v]) => ({ k, v }))
  const asset = e.by_asset.map((a) => ({ k: a.asset, v: a.long_usd + a.short_usd }))
  const ls = [
    { k: 'Long', v: e.long_usd },
    { k: 'Short', v: e.short_usd },
  ]
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">Exposure</h1>
        <p className="text-[13px] text-muted">
          Synthetic book notional. INR figures convert USD notional at a labelled demo FX rate of {fx.toFixed(2)}.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label="Total Position Exposure" value={inrFromUsd(e.total_usd, fx)} />
        <KpiCard label="Long Exposure" value={inrFromUsd(e.long_usd, fx)} />
        <KpiCard label="Short Exposure" value={inrFromUsd(e.short_usd, fx)} />
        <KpiCard label="Net Exposure" value={inrFromUsd(e.net_usd, fx)} />
        <KpiCard label="Gross Exposure" value={inrFromUsd(e.gross_usd, fx)} />
        <KpiCard label="Liquidation Exposure" value={inrFromUsd(e.liquidation_usd, fx)} tone="crit" />
        <KpiCard label="At-Risk Exposure" value={inrFromUsd(e.at_risk_usd, fx)} tone="warn" />
        <KpiCard label="Estimated Loss" value={inrFromUsd(e.estimated_loss_usd, fx)} tone="crit" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="EXPOSURE BY LEVERAGE">
          <div className="h-48">
            <ResponsiveContainer>
              <BarChart data={lev}>
                <XAxis dataKey="k" tick={{ fontSize: 10, fill: '#6B7280' }} />
                <YAxis hide />
                <Tooltip formatter={(v) => inrFromUsd(Number(v), fx)} contentStyle={{ border: '1px solid #E5E7EB', fontSize: 12 }} />
                <Bar dataKey="v" fill="#334E68" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="EXPOSURE BY ASSET">
          <div className="h-48">
            <ResponsiveContainer>
              <BarChart data={asset}>
                <XAxis dataKey="k" tick={{ fontSize: 10, fill: '#6B7280' }} />
                <YAxis hide />
                <Tooltip formatter={(v) => inrFromUsd(Number(v), fx)} contentStyle={{ border: '1px solid #E5E7EB', fontSize: 12 }} />
                <Bar dataKey="v" fill="#4B5563" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="LONG VS SHORT">
          <div className="h-48">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={ls} dataKey="v" nameKey="k" innerRadius={40} outerRadius={70} stroke="#fff">
                  <Cell fill="#334E68" />
                  <Cell fill="#9CA3AF" />
                </Pie>
                <Tooltip formatter={(v) => inrFromUsd(Number(v), fx)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>
      <Panel title="EXPOSURE APPROACHING LIQUIDATION">
        <p className="mb-2 text-[13px] tabular">
          Near-threshold exposure: <span className="font-medium">{inrFromUsd(e.approaching_liq_usd, fx)}</span>
        </p>
      </Panel>
      <div className="overflow-x-auto border border-line bg-card">
        <table className="min-w-full text-left text-[12px]">
          <thead className="border-b border-line bg-[#fafafa] text-[10px] tracking-wide text-muted">
            <tr>
              {['Asset', 'Long Exposure', 'Short Exposure', 'Net Exposure', 'At-Risk Exposure', 'Liquidation Exposure'].map(
                (h) => (
                  <th key={h} className="px-3 py-2 font-medium">
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {e.by_asset.map((a) => (
              <tr key={a.asset} className="border-b border-line">
                <td className="px-3 py-2">{a.asset}</td>
                <td className="tabular px-3 py-2">{inrFromUsd(a.long_usd, fx)}</td>
                <td className="tabular px-3 py-2">{inrFromUsd(a.short_usd, fx)}</td>
                <td className="tabular px-3 py-2">{inrFromUsd(a.net_usd, fx)}</td>
                <td className="tabular px-3 py-2">{inrFromUsd(a.at_risk_usd, fx)}</td>
                <td className="tabular px-3 py-2">{inrFromUsd(a.liquidation_usd, fx)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
