const FX = 83.5

export function inrFromUsd(usd: number, fx = FX): string {
  const inr = usd * fx
  const sign = inr < 0 ? '-' : ''
  const a = Math.abs(inr)
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} L`
  return `${sign}₹${a.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

export function usd(n: number, d = 2): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: d })
}

export function pct(n: number, d = 1): string {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(d)}%`
}

export function num(n: number, d = 0): string {
  return n.toLocaleString('en-US', { maximumFractionDigits: d })
}

export function statusClass(status: string): string {
  if (status === 'LIQUIDATED' || status === 'CRITICAL' || status === 'SEVERE') return 'text-crit'
  if (status === 'NEAR LIQUIDATION' || status === 'HIGH' || status === 'STRESSED') return 'text-crit'
  if (status === 'AT RISK' || status === 'MEDIUM' || status === 'WARNING' || status === 'ELEVATED') return 'text-warn'
  if (status === 'SAFE' || status === 'LOW' || status === 'NORMAL' || status === 'INFO') return 'text-safe'
  return 'text-muted'
}

export function statusBg(status: string): string {
  if (status === 'LIQUIDATED' || status === 'CRITICAL' || status === 'HIGH') return 'bg-[var(--crit-bg)] text-[var(--crit-fg)]'
  if (status === 'NEAR LIQUIDATION') return 'bg-[var(--crit-bg)] text-[var(--crit-fg)]'
  if (status === 'AT RISK' || status === 'MEDIUM' || status === 'WARNING') return 'bg-[var(--warn-bg)] text-[var(--warn-fg)]'
  if (status === 'SAFE' || status === 'LOW' || status === 'INFO') return 'bg-[var(--ok-bg)] text-[var(--ok-fg)]'
  return 'bg-bg text-muted'
}
