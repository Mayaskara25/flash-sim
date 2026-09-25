import { KpiCard, Panel } from '../components/KpiCard'
import { PriceChart } from '../components/PriceChart'
import { useSim } from '../context/SimContext'
import { num, pct, usd } from '../services/format'

export function MarketCrashPage() {
  const { overview, update } = useSim()
  if (!overview) return null
  const m = overview.market
  const p = overview.params
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-medium">Market Crash</h1>
        <p className="text-[13px] text-muted">Detailed monitoring of the simulated crash scenario.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard label="Asset" value={m.primary_asset} hint="Public/sample quote" />
        <KpiCard label="Current Price" value={usd(m.current_price)} />
        <KpiCard label="Starting Price" value={usd(m.starting_price)} />
        <KpiCard label="Price Change" value={pct(m.price_change_pct)} tone={m.price_change_pct < 0 ? 'crit' : 'safe'} />
        <KpiCard label="Volume" value={num(m.volume)} />
        <KpiCard label="Volume Change" value={pct(m.volume_change_pct, 0)} />
        <KpiCard label="Volatility" value={`${m.volatility_vs_baseline.toFixed(1)}x baseline`} />
        <KpiCard label="Crash Severity" value={m.crash_severity} tone={m.crash_mode ? 'crit' : 'neutral'} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Panel title="PRICE MOVEMENT">
            <PriceChart candles={m.candles} height={320} />
          </Panel>
        </div>
        <Panel title="CURRENT MARKET CONDITIONS">
          <dl className="space-y-2 text-[13px]">
            <Row k="Price decline" v={pct(m.price_change_pct)} />
            <Row k="Volatility" v={`${m.volatility_vs_baseline.toFixed(1)}x baseline`} />
            <Row k="Volume" v={`${(1 + m.volume_change_pct / 100).toFixed(1)}x baseline`} />
            <Row k="Liquidity" v={m.liquidity} />
            <Row k="Market state" v={m.market_state} />
          </dl>
          <p className="mt-4 text-[12px] leading-relaxed text-muted">
            The crash scenario is simulated. It is used to evaluate how leveraged positions respond under stressed market
            conditions.
          </p>
        </Panel>
      </div>
      <Panel title="CRASH SCENARIO CONTROLS">
        <div className="grid gap-4 md:grid-cols-4">
          <label className="text-[12px] text-muted">
            Crash magnitude {p.crash_pct.toFixed(1)}%
            <input
              className="mt-2 w-full"
              type="range"
              min={0}
              max={25}
              step={0.5}
              value={p.crash_pct}
              onChange={(e) => void update({ crash_magnitude: Number(e.target.value) })}
            />
          </label>
          <label className="text-[12px] text-muted">
            Simulation duration
            <select
              className="mt-2 w-full border border-line px-2 py-1 text-ink"
              value={p.horizon_minutes}
              onChange={(e) => void update({ horizon_minutes: Number(e.target.value) })}
            >
              {[5, 15, 30, 60].map((v) => (
                <option key={v} value={v}>
                  {v} min
                </option>
              ))}
            </select>
          </label>
          <label className="text-[12px] text-muted">
            Volatility
            <select
              className="mt-2 w-full border border-line px-2 py-1 text-ink"
              value={p.volatility}
              onChange={(e) => void update({ volatility: e.target.value })}
            >
              {['Low', 'Medium', 'High'].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label className="text-[12px] text-muted">
            Liquidity
            <select
              className="mt-2 w-full border border-line px-2 py-1 text-ink"
              value={p.liquidity}
              onChange={(e) => void update({ liquidity: e.target.value })}
            >
              {['Normal', 'Reduced', 'Severely Reduced'].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
        </div>
      </Panel>
    </div>
  )
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between border-b border-line py-1">
      <dt className="text-muted">{k}</dt>
      <dd className="tabular font-medium">{v}</dd>
    </div>
  )
}
