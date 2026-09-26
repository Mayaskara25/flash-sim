import { roleLabel } from '../format'
import type { LogEntry, SignalView } from '../types'
import { Badge } from '../ui'

/**
 * H14: the timeline is a decision record, not an event firehose.
 *
 * Transitions, decisions and comms come first, then the *first* alert for
 * each signal — repeats of a signal already on the key-signals tiles are
 * noise (H12/H13 review finding 4). Roles read IC / TL / CS, never
 * P1/P2/P3, and alert rows use the signal's plain label rather than its code.
 */
export function IncidentTimeline({ log, signals = [], limit = 6 }: { log: LogEntry[]; signals?: SignalView[]; limit?: number }) {
  const labels = new Map(signals.map((signal) => [signal.code, signal.label]))
  const seenSignals = new Set<string>()

  /** Signal a log row is about, or null when it is not a signal-level alert. */
  const signalOf = (entry: LogEntry): string | null => {
    for (const code of labels.keys()) {
      if (new RegExp(`\\b${code}\\b`).test(entry.action)) return code
    }
    return null
  }

  const scored: { entry: LogEntry; group: number }[] = []
  for (const entry of log) {
    if (entry.type === 'transition' || entry.type === 'decision' || entry.type === 'comm') {
      scored.push({ entry, group: 0 })
      continue
    }
    if (entry.type !== 'alert') continue // free-text notes live in the full log
    const code = signalOf(entry)
    if (code === null || seenSignals.has(code)) continue
    seenSignals.add(code)
    scored.push({ entry, group: 1 })
  }

  // Each group newest-first, then the first alerts, then cap at `limit`.
  const ordered = [0, 1].flatMap((group) => scored.filter((item) => item.group === group).reverse())
  const shown = ordered.slice(0, limit)
  const hidden = ordered.length - shown.length

  return <section aria-label="Incident timeline" style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 8, padding: 12 }}>
    <div className="flex items-baseline justify-between gap-2">
      <h2 className="text-label" style={{ color: 'var(--muted)' }}>Timeline</h2>
      <span className="text-xs" style={{ color: 'var(--muted)' }}>last {shown.length} key events</span>
    </div>
    {shown.length === 0
      ? <p className="text-body mt-2" style={{ color: 'var(--muted)' }}>The timeline begins when a scenario starts.</p>
      : <ol className="mt-1.5 divide-y" style={{ borderColor: 'var(--line)' }}>
        {shown.map(({ entry }) => <li key={entry.id} className="grid grid-cols-[52px_1fr] gap-2 py-1.5">
          <span className="font-mono text-xs tabular" style={{ color: 'var(--muted)' }}>{entry.t_label}</span>
          <div className="min-w-0">
            <p className="text-body leading-snug">
              {entry.actor === 'system'
                ? <><span className="font-semibold">Engine</span>{' '}</>
                : <span className="mr-1 inline-flex align-middle"><Badge tone={entry.actor === 'IC' ? 'sev1' : entry.actor === 'TL' ? 'sev2' : 'sev3'} title={roleLabel[entry.actor]}>{entry.actor}</Badge></span>}
              {describe(entry, labels)}
            </p>
            {entry.rationale && <p className="text-body mt-0.5 leading-snug" style={{ color: 'var(--muted)' }}>Why: {entry.rationale}</p>}
          </div>
        </li>)}
      </ol>}
    {hidden > 0 && <p className="text-body mt-1" style={{ color: 'var(--muted)' }}>+{hidden} more in Details › Log</p>}
  </section>
}

/**
 * Alert rows read as words ("Liquidation rate · critical"), never raw codes.
 * The backend writes them as `<CODE> <level> alert` or `Tag <tag> added: …`.
 */
function describe(entry: LogEntry, labels: Map<string, string>): string {
  if (entry.type !== 'alert') return entry.action
  for (const [code, label] of labels) {
    if (new RegExp(`\\b${code}\\b`).test(entry.action)) {
      const level = /\b(critical|warn)\b/.exec(entry.action)?.[1] ?? 'threshold crossed'
      return `${label} · ${level}`
    }
  }
  return entry.action.replace(/^Tag (\w+) added: /, 'Scenario tag $1 · ')
}
