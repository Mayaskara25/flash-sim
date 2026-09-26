import { tagFullName, tagName } from '../format'

export type TagProps = {
  code: string
  active?: boolean
}

/**
 * H13 primitive: scenario tag as `CODE · short name`,
 * with the full catalogue name in the tooltip.
 */
export function Tag({ code, active = true }: TagProps) {
  return (
    <span
      title={`${code} · ${tagFullName(code)}`}
      aria-label={`${code} · ${tagFullName(code)}`}
      data-active={active}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        borderRadius: 6,
        border: '1px solid var(--line)',
        padding: '4px 10px',
        fontSize: 12,
        fontWeight: 600,
        lineHeight: '1.25rem',
        whiteSpace: 'nowrap',
        background: active ? 'var(--ink)' : 'transparent',
        color: active ? 'var(--bg)' : 'var(--muted)',
        borderColor: active ? 'var(--ink)' : 'var(--line)',
      }}
    >
      <span aria-hidden="true">{code}</span>
      <span aria-hidden="true" style={{ opacity: 0.55 }}>
        ·
      </span>
      <span>{tagName(code)}</span>
    </span>
  )
}
