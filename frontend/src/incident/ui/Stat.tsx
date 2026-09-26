export type StatStatus = 'normal' | 'watch' | 'warn' | 'critical' | 'ok'

export type StatProps = {
  label: string
  value: string
  unit?: string
  status?: StatStatus
  trend?: string
}

const STATUS_COLOR: Record<StatStatus, string> = {
  normal: 'var(--ok-fg)',
  ok: 'var(--ok-fg)',
  watch: 'var(--sev4-fg)',
  warn: 'var(--warn-fg)',
  critical: 'var(--crit-fg)',
}

/** H13 primitive: big projector-legible number with label, unit and status. */
export function Stat({ label, value, unit, status = 'normal', trend }: StatProps) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderLeft: `4px solid ${STATUS_COLOR[status]}`,
        borderRadius: 8,
        padding: '12px 16px',
        minWidth: 0,
      }}
    >
      <div className="text-label" style={{ color: 'var(--muted)' }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 4 }}>
        <span className="text-stat" style={{ color: STATUS_COLOR[status] }}>
          {value}
        </span>
        {unit && (
          <span className="text-body" style={{ color: 'var(--muted)' }}>
            {unit}
          </span>
        )}
      </div>
      {trend && (
        <div className="text-label" style={{ color: 'var(--muted)', marginTop: 4, textTransform: 'none', letterSpacing: 0 }}>
          {trend}
        </div>
      )}
    </div>
  )
}
