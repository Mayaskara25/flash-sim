import { useEffect, useState } from 'react'
import { api } from '../services/api'

export function DataStatus() {
  const [d, setD] = useState<Record<string, string> | null>(null)
  useEffect(() => {
    void api.dataStatus().then(setD)
  }, [])
  if (!d) return null
  const rows = [
    ['Market data', d.market_data],
    ['Trader positions', d.trader_positions],
    ['Crash', d.crash],
    ['Monte Carlo', d.monte_carlo],
    ['AI model', d.ai_model],
  ]
  return (
    <div className="border border-line bg-bg p-2.5 text-[10px] leading-4 text-muted">
      <div className="mb-1 font-medium tracking-wide text-ink">DATA STATUS</div>
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-2">
          <span>{k}</span>
          <span className="text-right text-ink">{v}</span>
        </div>
      ))}
    </div>
  )
}
