import { KpiCard, Panel } from '../components/KpiCard'
import { PriceChart } from '../components/PriceChart'
import { useSim } from '../context/SimContext'
import { num, pct, usd } from '../services/format'

export function OverviewPage() {
  const { overview, update } = useSim()
  if (!overview) return null
  const { kpis, market, params } = overview
  const down = kpis.price_change_pct < 0
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">P2 Risk Engine</h1>
        <p className="text-sm text-muted">Market Crash &amp; Liquidation Intelligence</p>
        <p className="mt-1 max-w-3xl text-[13px] text-muted">
          Monitor leveraged exposure, identify liquidation clusters, simulate crash scenarios and estimate cascade risk.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div>
          <div className="text-[10px] tracking-wide text-muted">MARKET STATUS</div>
          <div className="text-sm font-medium">{market.market_state}</div>
        </div>
        <div className={`border px-2 py-1 text-[11px] ${market.crash_mode ? 'border-[#e8d0d0] bg-[var(--crit-bg)] text-[var(--crit-fg)]' : 'border-line text-muted'}`}>
          {market.crash_mode ? 'CRASH MODE' : 'NORMAL'}
        </div>
        <span className="text-[10px] text-muted">KPI values are SIMULATED</span>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
        <KpiCard label="Current Price" value={usd(kpis.current_price)} hint="SIMULATED overlay on sample series" />
        <KpiCard label="Price Change" value={pct(kpis.price_change_pct)} tone={down ? 'crit' : 'safe'} hint="SIMULATED" />
        <KpiCard label="Volatility" value={kpis.volatility} tone={kpis.volatility === 'High' ? 'warn' : 'neutral'} hint="SIMULATED" />
        <KpiCard label="Volume Change" value={pct(kpis.volume_change_pct, 0)} hint="SIMULATED" />
        <KpiCard label="Total Positions" value={num(kpis.total_positions)} hint="Synthetic book" />
        <KpiCard label="Positions At Risk" value={num(kpis.positions_at_risk)} tone="warn" hint="SIMULATED" />
        <KpiCard label="Estimated Liquidations" value={num(kpis.estimated_liquidations)} tone="crit" hint="Modelled" />
        <KpiCard
          label="Cascade Risk"
          value={`${kpis.cascade_risk} / 100`}
          tone={kpis.cascade_risk >= 62 ? 'crit' : kpis.cascade_risk >= 38 ? 'warn' : 'safe'}
          hint="Research indicator"
        />
      </div>

      <Panel
        title="PRIMARY ASSET PATH (NVDA) — SAMPLE + SIMULATED CRASH"
        footnote="Chart combines a labelled historical/public-style sample path with a simulated crash overlay. It is not live exchange data."
      >
        <div className="mb-3 max-w-md text-[12px] text-muted">
          Crash magnitude {params.crash_pct.toFixed(1)}%
          <input
            className="mt-1 w-full"
            type="range"
            min={0}
            max={25}
            step={0.5}
            value={params.crash_pct}
            onChange={(e) => void update({ crash_magnitude: Number(e.target.value) })}
          />
          <div className="mt-1 flex justify-between text-[10px]">
            <span>0%</span>
            <span>25%</span>
          </div>
        </div>
        <PriceChart candles={market.candles} />
      </Panel>
    </div>
  )
}
