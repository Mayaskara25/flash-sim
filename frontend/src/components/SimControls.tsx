import { useSim } from '../context/SimContext'

export function SimControls() {
  const { params, update, loading, error } = useSim()
  if (!params) return null
  return (
    <section className="border-b border-line bg-white px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[11px] font-medium tracking-wide text-muted">GLOBAL SIMULATION CONTROL</h2>
        <span className="text-[10px] text-muted">Research Simulation — Public/Historical Market Data + Synthetic Positions</span>
      </div>
      {error && <div className="mb-2 text-[12px] text-crit">{error}</div>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-7">
        <label className="text-[11px] text-muted">
          Crash {params.crash_pct.toFixed(1)}%
          <input
            className="mt-1 w-full"
            type="range"
            min={0}
            max={25}
            step={0.5}
            disabled={loading}
            value={params.crash_pct}
            onChange={(e) => void update({ crash_magnitude: Number(e.target.value) })}
          />
        </label>
        <label className="text-[11px] text-muted">
          Volatility
          <select
            className="mt-1 w-full border border-line bg-white px-2 py-1 text-[12px] text-ink"
            value={params.volatility}
            onChange={(e) => void update({ volatility: e.target.value })}
          >
            {['Low', 'Medium', 'High'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-muted">
          Liquidity
          <select
            className="mt-1 w-full border border-line bg-white px-2 py-1 text-[12px] text-ink"
            value={params.liquidity}
            onChange={(e) => void update({ liquidity: e.target.value })}
          >
            {['Normal', 'Reduced', 'Severely Reduced'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-muted">
          Traders
          <select
            className="mt-1 w-full border border-line bg-white px-2 py-1 text-[12px] text-ink"
            value={params.n_traders}
            onChange={(e) => void update({ n_traders: Number(e.target.value) })}
          >
            {[1000, 2500, 5000, 10000].map((v) => (
              <option key={v} value={v}>
                {v.toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-muted">
          Avg leverage {params.avg_leverage.toFixed(1)}x
          <input
            className="mt-1 w-full"
            type="range"
            min={5}
            max={22}
            step={0.1}
            value={params.avg_leverage}
            onChange={(e) => void update({ avg_leverage: Number(e.target.value) })}
          />
        </label>
        <label className="text-[11px] text-muted">
          Long {params.long_pct.toFixed(0)}% / Short {params.short_pct.toFixed(0)}%
          <input
            className="mt-1 w-full"
            type="range"
            min={0.35}
            max={0.85}
            step={0.01}
            value={params.long_ratio}
            onChange={(e) => void update({ long_ratio: Number(e.target.value) })}
          />
        </label>
        <label className="text-[11px] text-muted">
          Horizon
          <select
            className="mt-1 w-full border border-line bg-white px-2 py-1 text-[12px] text-ink"
            value={params.horizon_minutes}
            onChange={(e) => void update({ horizon_minutes: Number(e.target.value) })}
          >
            {[5, 15, 30, 60].map((v) => (
              <option key={v} value={v}>
                {v} min
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  )
}
