import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { KpiCard, Panel } from '../components/KpiCard'
import { useSim } from '../context/SimContext'
import { api } from '../services/api'
import { inrFromUsd, num, pct } from '../services/format'
import type { MonteCarlo } from '../types'

export function MonteCarloPage() {
  const { params, revision } = useSim()
  const [n, setN] = useState(1000)
  const [crash, setCrash] = useState(10)
  const [vol, setVol] = useState('High')
  const [horizon, setHorizon] = useState(30)
  const [mc, setMc] = useState<MonteCarlo | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!params) return
    setCrash(Math.round(params.crash_pct) || 8)
    setVol(params.volatility)
    setHorizon(params.horizon_minutes)
  }, [params, revision])

  const run = async (sims = n) => {
    setBusy(true)
    try {
      const r = await api.monteCarlo({
        n_simulations: sims,
        crash_severity: crash,
        volatility: vol,
        time_horizon_minutes: horizon,
      })
      setMc(r)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void run(1000)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revision])

  const pathData = useMemo(() => {
    if (!mc) return []
    return mc.median_path.map((med, i) => {
      const row: Record<string, number> = {
        t: i,
        median: med,
        severe: mc.severe_path[i],
        start: mc.start_price,
      }
      mc.paths_sample.forEach((p, j) => {
        row[`p${j}`] = p[i]
      })
      return row
    })
  }, [mc])

  const fx = mc?.usd_inr ?? 83.5

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">MONTE CARLO STRESS TEST</h1>
        <p className="max-w-3xl text-[13px] text-muted">
          Generate thousands of possible price paths under specified assumptions and evaluate potential liquidation
          outcomes.
        </p>
      </div>
      <Panel title="CONTROLS">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="text-[12px] text-muted">
            Number of simulations
            <select className="mt-1 w-full border border-line px-2 py-1 text-ink" value={n} onChange={(e) => setN(Number(e.target.value))}>
              {[1000, 5000, 10000].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label className="text-[12px] text-muted">
            Crash severity
            <select className="mt-1 w-full border border-line px-2 py-1 text-ink" value={crash} onChange={(e) => setCrash(Number(e.target.value))}>
              {[5, 10, 15, 20].map((v) => (
                <option key={v} value={v}>
                  {v}%
                </option>
              ))}
            </select>
          </label>
          <label className="text-[12px] text-muted">
            Volatility
            <select className="mt-1 w-full border border-line px-2 py-1 text-ink" value={vol} onChange={(e) => setVol(e.target.value)}>
              {['Low', 'Medium', 'High'].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label className="text-[12px] text-muted">
            Time horizon
            <select className="mt-1 w-full border border-line px-2 py-1 text-ink" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
              {[5, 15, 30, 60].map((v) => (
                <option key={v} value={v}>
                  {v}m
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end">
            <button
              type="button"
              disabled={busy}
              onClick={() => void run(n)}
              className="w-full border border-navy bg-navy px-3 py-1.5 text-[12px] text-white disabled:opacity-50"
            >
              {busy ? 'Running…' : 'Run simulation'}
            </button>
          </div>
        </div>
      </Panel>
      {mc && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <KpiCard label="Simulations" value={num(mc.n_simulations)} />
            <KpiCard label="Average liquidations" value={num(mc.average_liquidations, 0)} hint="SIMULATED" />
            <KpiCard label="Median liquidations" value={num(mc.median_liquidations, 0)} />
            <KpiCard label="Worst-case simulated" value={num(mc.worst_case_liquidations)} tone="crit" />
            <KpiCard label="Average exposure" value={inrFromUsd(mc.average_exposure_usd, fx)} />
            <KpiCard label="Maximum simulated exposure" value={inrFromUsd(mc.max_exposure_usd, fx)} tone="warn" />
            <KpiCard
              label="Severe cascade scenarios"
              value={pct(mc.severe_cascade_frequency * 100, 1)}
              hint={mc.label}
              tone="crit"
            />
            <KpiCard label="Avg. modelled loss" value={inrFromUsd(mc.average_loss_usd, fx)} />
          </div>
          <Panel title="PRICE PATH ENSEMBLE" footnote={mc.disclaimer}>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={pathData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <XAxis dataKey="t" tick={{ fontSize: 10, fill: 'var(--chart-axis)' }} axisLine={{ stroke: 'var(--chart-grid)' }} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: 'var(--chart-axis)' }} width={48} axisLine={{ stroke: 'var(--chart-grid)' }} />
                  <Tooltip contentStyle={{ border: '1px solid #E5E7EB', fontSize: 12 }} />
                  {mc.paths_sample.map((_, i) => (
                    <Line key={i} type="monotone" dataKey={`p${i}`} stroke="var(--chart-grid)" strokeWidth={0.7} dot={false} legendType="none" isAnimationActive={false} />
                  ))}
                  <Line type="monotone" dataKey="start" stroke="var(--chart-2)" strokeDasharray="4 3" strokeWidth={1} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="median" stroke="var(--chart-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="severe" stroke="var(--chart-crit)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex gap-4 text-[11px] text-muted">
              <span>Gray — sampled paths</span>
              <span>Navy — median</span>
              <span>Muted red — severe path</span>
              <span>Dashed — starting price</span>
            </div>
          </Panel>
          <div className="grid gap-4 md:grid-cols-2">
            <Hist title="DISTRIBUTION OF FINAL PRICES" data={mc.price_hist} />
            <Hist title="DISTRIBUTION OF LIQUIDATIONS" data={mc.liquidation_hist} />
            <Hist title="DISTRIBUTION OF LOSSES (USD m)" data={mc.loss_hist_usd_m} />
            <Hist title="DISTRIBUTION OF PLATFORM EXPOSURE (USD m)" data={mc.exposure_hist_usd_m} />
          </div>
        </>
      )}
    </div>
  )
}

function Hist({ title, data }: { title: string; data: { centers: number[]; counts: number[] } }) {
  const rows = data.centers.map((c, i) => ({ x: Number(c.toFixed(2)), n: data.counts[i] }))
  return (
    <Panel title={title}>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <XAxis dataKey="x" tick={{ fontSize: 10, fill: 'var(--chart-axis)' }} />
            <YAxis tick={{ fontSize: 10, fill: 'var(--chart-axis)' }} />
            <Tooltip contentStyle={{ border: '1px solid #E5E7EB', fontSize: 12 }} />
            <Bar isAnimationActive={false} dataKey="n" fill="var(--chart-axis)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  )
}
