import { useEffect, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { KpiCard, Panel } from '../components/KpiCard'
import { useSim } from '../context/SimContext'
import { api } from '../services/api'
import { inrFromUsd, num, pct, statusBg, usd } from '../services/format'
import type { Anomaly, LiqSummary, PositionRow } from '../types'

export function LiquidationMonitorPage() {
  const { revision, overview } = useSim()
  const [summary, setSummary] = useState<LiqSummary | null>(null)
  const [rows, setRows] = useState<PositionRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [anoms, setAnoms] = useState<Anomaly[]>([])
  const [asset, setAsset] = useState('')
  const [side, setSide] = useState('')
  const [status, setStatus] = useState('')
  const [levMin, setLevMin] = useState('')
  const [distMax, setDistMax] = useState('')

  useEffect(() => {
    void api.liquidations().then(setSummary)
    void api.anomalies().then((r) => setAnoms(r.items))
  }, [revision])

  useEffect(() => {
    const q = new URLSearchParams({ page: String(page), page_size: '25' })
    if (asset) q.set('asset', asset)
    if (side) q.set('side', side)
    if (status) q.set('status', status)
    if (levMin) q.set('leverage_min', levMin)
    if (distMax) q.set('distance_max', distMax)
    void api.positions(q.toString()).then((r) => {
      setRows(r.rows)
      setTotal(r.total_filtered)
    })
  }, [revision, page, asset, side, status, levMin, distMax])

  const hist = summary
    ? Object.entries(summary.leverage_histogram).map(([k, v]) => ({ lev: k, n: v }))
    : []
  const fx = overview?.market.usd_inr ?? 83.5

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">Liquidation Monitor</h1>
        <p className="text-[13px] text-muted">
          Synthetic book. Calculations run on the full dataset; the table is a filtered subset. Liquidation prices are a{' '}
          <span className="text-ink">modelled liquidation threshold</span>, not a proprietary engine replica.
        </p>
      </div>
      {summary && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <KpiCard label="Total Positions" value={num(summary.total)} hint="Synthetic" />
          <KpiCard label="Safe" value={num(summary.safe)} tone="safe" />
          <KpiCard label="At Risk" value={num(summary.at_risk)} tone="warn" />
          <KpiCard label="Near Liquidation" value={num(summary.near_liquidation)} tone="crit" />
          <KpiCard label="Liquidated" value={num(summary.liquidated)} tone="crit" />
        </div>
      )}
      <Panel title="NUMBER OF POSITIONS BY LEVERAGE">
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hist}>
              <XAxis dataKey="lev" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={{ stroke: '#E5E7EB' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={{ stroke: '#E5E7EB' }} />
              <Tooltip contentStyle={{ border: '1px solid #E5E7EB', fontSize: 12 }} />
              <Bar dataKey="n" fill="#334E68" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
      <Panel title="FILTERS">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <select className="border border-line px-2 py-1 text-[12px]" value={asset} onChange={(e) => { setPage(1); setAsset(e.target.value) }}>
            <option value="">Asset — all</option>
            {['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN'].map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
          <select className="border border-line px-2 py-1 text-[12px]" value={side} onChange={(e) => { setPage(1); setSide(e.target.value) }}>
            <option value="">Long / Short</option>
            <option>LONG</option>
            <option>SHORT</option>
          </select>
          <select className="border border-line px-2 py-1 text-[12px]" value={levMin} onChange={(e) => { setPage(1); setLevMin(e.target.value) }}>
            <option value="">Leverage — all</option>
            <option value="10">≥ 10x</option>
            <option value="15">≥ 15x</option>
            <option value="20">≥ 20x</option>
          </select>
          <select className="border border-line px-2 py-1 text-[12px]" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value) }}>
            <option value="">Risk status — all</option>
            {['SAFE', 'AT RISK', 'NEAR LIQUIDATION', 'LIQUIDATED'].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select className="border border-line px-2 py-1 text-[12px]" value={distMax} onChange={(e) => { setPage(1); setDistMax(e.target.value) }}>
            <option value="">Distance to liq — all</option>
            <option value="1.25">≤ 1.25%</option>
            <option value="4">≤ 4%</option>
            <option value="10">≤ 10%</option>
          </select>
        </div>
      </Panel>
      <div className="overflow-x-auto border border-line bg-card">
        <table className="min-w-full text-left text-[12px]">
          <thead className="border-b border-line bg-[#fafafa] text-[10px] tracking-wide text-muted">
            <tr>
              {[
                'Trader ID',
                'Asset',
                'Side',
                'Entry',
                'Current',
                'Qty',
                'Leverage',
                'Initial Margin',
                'Unrealized P&L',
                'Liq. Price',
                'Dist. to Liq.',
                'Status',
              ].map((h) => (
                <th key={h} className="px-2 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.trader_id} className="border-b border-line">
                <td className="px-2 py-1.5 font-mono text-[11px]">{r.trader_id}</td>
                <td className="px-2 py-1.5">{r.asset}</td>
                <td className="px-2 py-1.5">{r.side}</td>
                <td className="tabular px-2 py-1.5">{usd(r.entry_price)}</td>
                <td className="tabular px-2 py-1.5">{usd(r.current_price)}</td>
                <td className="tabular px-2 py-1.5">{num(r.quantity, 1)}</td>
                <td className="tabular px-2 py-1.5">{r.leverage}x</td>
                <td className="tabular px-2 py-1.5">{inrFromUsd(r.initial_margin_usd, fx)}</td>
                <td className={`tabular px-2 py-1.5 ${r.unrealized_pnl_usd < 0 ? 'text-crit' : 'text-safe'}`}>
                  {inrFromUsd(r.unrealized_pnl_usd, fx)}
                </td>
                <td className="tabular px-2 py-1.5">{usd(r.liquidation_price)}</td>
                <td className="tabular px-2 py-1.5">{pct(r.distance_to_liquidation_pct, 2)}</td>
                <td className="px-2 py-1.5">
                  <span className={`px-1.5 py-0.5 text-[10px] ${statusBg(r.status)}`}>{r.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex items-center justify-between px-3 py-2 text-[11px] text-muted">
          <span>
            Showing {rows.length} of {total.toLocaleString()} filtered · full synthetic book used in calculations
          </span>
          <div className="flex gap-2">
            <button className="border border-line px-2 py-0.5" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Prev
            </button>
            <span>Page {page}</span>
            <button
              className="border border-line px-2 py-0.5"
              disabled={page * 25 >= total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
      <Panel title="ABNORMAL ACTIVITY" footnote="These are simulated anomalies versus a synthetic baseline (z-score / concentration rules).">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-[12px]">
            <thead className="text-[10px] tracking-wide text-muted">
              <tr>
                <th className="py-1 font-medium">Severity</th>
                <th className="py-1 font-medium">Time</th>
                <th className="py-1 font-medium">Asset</th>
                <th className="py-1 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {anoms.map((a) => (
                <tr key={a.code + a.description} className="border-t border-line">
                  <td className="py-2">
                    <span className={`px-1.5 py-0.5 text-[10px] ${statusBg(a.severity)}`}>{a.severity}</span>
                  </td>
                  <td className="py-2 text-muted">{a.time}</td>
                  <td className="py-2">{a.asset}</td>
                  <td className="py-2">{a.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
