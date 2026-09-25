import type { Role } from './types'

const phases = [
  { until: 600, name: 'Detect', focus: {
    IC: 'Acknowledge alert, read classifier result, set initial severity.',
    TL: 'Check feed freshness, engine errors and latency.',
    CS: 'Open ticket dashboard; hold public comms until approved.',
  } },
  { until: 1200, name: 'Escalate', focus: {
    IC: 'Choose protective controls; page founders if SEV-1.',
    TL: 'Rule in or out engine, overload and pricing faults.',
    CS: 'Approve first customer notice and send the support FAQ.',
  } },
  { until: 2400, name: 'Contain', focus: {
    IC: 'Watch fund and exposure; decide top-up, ADL or haircut.',
    TL: 'Fix or roll back; load-shed if needed.',
    CS: 'Update every 15–20 minutes and notify partners when involved.',
  } },
  { until: 3600, name: 'Stabilise', focus: {
    IC: 'Confirm de-escalation; review and lift time-boxed controls.',
    TL: 'Verify recovery metrics and preserve evidence.',
    CS: 'Prepare monitoring or resolution notice.',
  } },
  { until: Infinity, name: 'Close', focus: {
    IC: 'Sign off final state; open compensation review if needed.',
    TL: 'Write technical root cause.',
    CS: 'Send resolution notice and clear support backlog.',
  } },
] as const

export function roleFocus(t: number, role: Role | 'All'): { phase: string; text: string } {
  const current = phases.find((phase) => t < phase.until) ?? phases[phases.length - 1]
  const text = role === 'All' ? 'IC: ' + current.focus.IC + ' TL: ' + current.focus.TL + ' CS: ' + current.focus.CS : current.focus[role === 'system' ? 'IC' : role]
  return { phase: current.name, text }
}
