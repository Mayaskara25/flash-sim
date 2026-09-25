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

export function simLabel(t: number): string {
  const sign = t < 0 ? '-' : '+'
  const x = Math.abs(Math.trunc(t))
  return `T${sign}${String(Math.floor(x / 60)).padStart(2, '0')}:${String(x % 60).padStart(2, '0')}`
}

export function activeTags(state: IncidentStateDTO): string[] {
  return state.tags.filter((tag) => tag.active).map((tag) => tag.tag)
}
