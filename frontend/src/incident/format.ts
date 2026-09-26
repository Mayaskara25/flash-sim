import type { IncidentStateDTO, Role, SignalStatus } from './types'

export const severityTone: Record<number, string> = {
  1: 'border-red-700 bg-red-950 text-white',
  2: 'border-orange-600 bg-orange-950 text-white',
  3: 'border-amber-500 bg-amber-950 text-white',
  4: 'border-slate-600 bg-slate-950 text-white',
}

export const signalTone: Record<SignalStatus, string> = {
  normal: 'text-safe bg-green-50 border-green-200',
  watch: 'text-blue-700 bg-blue-50 border-blue-200',
  warn: 'text-amber-800 bg-amber-50 border-amber-300',
  critical: 'text-red-800 bg-red-50 border-red-300',
}

export const roles: Role[] = ['IC', 'TL', 'CS']
export const roleLabel: Record<Role, string> = {
  IC: 'Incident Commander', TL: 'Tech Lead', CS: 'Comms / Support', system: 'System',
}

export function fmtNumber(n: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: Math.abs(n) < 10 ? 2 : 1 }).format(n)
}

/** H13: whole numbers with thousands separators, e.g. 410 -> "410", 12345 -> "12,345". */
export function fmtInt(n: number): string {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

/** H13: percentages with exactly 1 decimal place, e.g. 9.84 -> "9.8%". */
export function fmtPct(n: number, digits = 1): string {
  return `${n.toFixed(digits)}%`
}

export function simLabel(t: number): string {
  const sign = t < 0 ? '-' : '+'
  const x = Math.abs(Math.trunc(t))
  return `T${sign}${String(Math.floor(x / 60)).padStart(2, '0')}:${String(x % 60).padStart(2, '0')}`
}

/** H13 alias: simulation clock as `T+MM:SS` (wraps {@link simLabel}). */
export function fmtClock(t: number): string {
  return simLabel(t)
}

export function activeTags(state: IncidentStateDTO): string[] {
  return state.tags.filter((tag) => tag.active).map((tag) => tag.tag)
}

/**
 * H13 scenario-tag names.
 * Short names go on the tag itself (`M2 · Insurance fund drain`);
 * full catalogue names go in the tooltip. Full names mirror
 * `backend/incident/rules/tags.py::TAG_NAMES` (SPEC §4).
 */
export const TAG_SHORT_NAMES: Record<string, string> = {
  M1: 'Flash crash',
  M2: 'Insurance fund drain',
  M3: 'Price gap',
  M4: 'Oracle fault',
  M5: 'Gamma loss',
  M6: 'Whale unwind',
  S1: 'Stablecoin depeg',
  S2: 'Chain freeze',
  S3: 'Hedge outage',
  S4: 'Withdrawal run',
  S5: 'Basis blowout',
  P1: 'Engine bug',
  P2: 'API overload',
  P3: 'Key compromise',
  R1: 'Bank rail freeze',
  R2: 'Regulatory action',
  I1: 'Customer panic',
  I2: 'Insolvency rumour',
}

export const TAG_FULL_NAMES: Record<string, string> = {
  M1: 'Directional flash crash',
  M2: 'Liquidation cascade drains insurance fund',
  M3: 'Price gap → negative balances',
  M4: 'Mark-price oracle stale, wrong or manipulated',
  M5: 'Options volatility spike: short-gamma loss',
  M6: 'Concentrated (whale) position unwind',
  S1: 'Collateral stablecoin depeg',
  S2: 'Stablecoin chain congestion, issuer freeze or blacklist',
  S3: 'Hedge venue / liquidity provider outage or freeze',
  S4: 'Withdrawal run exceeds hot wallet + INR float',
  S5: 'INR ↔ USDT basis blowout',
  P1: 'Liquidation / risk engine bug',
  P2: 'Matching engine / API overload',
  P3: 'Hot wallet / key compromise',
  R1: 'UPI / banking partner freeze or throttle',
  R2: 'Regulatory action or access blocking',
  I1: 'Customer panic / information cascade',
  I2: 'Insolvency rumour / impersonation scams',
}

/** Short display name for a scenario tag, e.g. `M2 → "Insurance fund drain"`. */
export function tagName(tag: string): string {
  return TAG_SHORT_NAMES[tag] ?? TAG_FULL_NAMES[tag] ?? tag
}

/** Full catalogue name for tooltips, e.g. `M2 → "Liquidation cascade drains insurance fund"`. */
export function tagFullName(tag: string): string {
  return TAG_FULL_NAMES[tag] ?? TAG_SHORT_NAMES[tag] ?? tag
}
