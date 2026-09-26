import type { ReactNode } from 'react'

export type PanelProps = {
  title: string
  action?: ReactNode
  children: ReactNode
  className?: string
  id?: string
}

/** H13 primitive: titled card. Layout only — no business logic. */
export function Panel({ title, action, children, className, id }: PanelProps) {
  return (
    <section
      id={id}
      aria-label={title}
      className={className}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--line)',
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <h2 className="text-label" style={{ color: 'var(--muted)', margin: 0 }}>
          {title}
        </h2>
        {action}
      </div>
      <div className="text-body" style={{ marginTop: 12 }}>
        {children}
      </div>
    </section>
  )
}
