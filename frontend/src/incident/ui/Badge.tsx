import type { ReactNode } from 'react'

export type BadgeTone = 'sev1' | 'sev2' | 'sev3' | 'sev4' | 'ok' | 'warn' | 'crit' | 'neutral' | 'normal' | 'watch'

export type BadgeProps = {
  tone?: BadgeTone
  children: ReactNode
  title?: string
}

const TONE_VAR: Record<BadgeTone, string> = {
  sev1: 'sev1',
  crit: 'crit',
  sev2: 'sev2',
  sev3: 'sev3',
  warn: 'warn',
  sev4: 'sev4',
  neutral: 'sev4',
  normal: 'ok',
  ok: 'ok',
  watch: 'sev4',
}

/**
 * H13 primitive: status/severity pill. Always carries text —
 * never colour alone (UI_PLAN rule 5).
 */
export function Badge({ tone = 'neutral', children, title }: BadgeProps) {
  const key = TONE_VAR[tone]
  return (
    <span
      title={title}
      style={{
        display: 'inline-block',
        background: `var(--${key}-bg)`,
        color: `var(--${key}-fg)`,
        border: `1px solid var(--${key}-border)`,
        borderRadius: 999,
        padding: '2px 10px',
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        lineHeight: '1.5rem',
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  )
}
