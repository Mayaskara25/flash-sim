import type { ReactNode } from 'react'

export function KpiCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: string
  hint?: string
  tone?: 'crit' | 'warn' | 'safe' | 'neutral'
}) {
  const color =
    tone === 'crit' ? 'text-crit' : tone === 'warn' ? 'text-warn' : tone === 'safe' ? 'text-safe' : 'text-ink'
  return (
    <div className="border border-line bg-card p-3 shadow-[0_1px_1px_rgba(17,24,39,0.04)]">
      <div className="text-[10px] tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-xl tabular ${color}`}>{value}</div>
      {hint && <div className="mt-1 text-[10px] text-muted">{hint}</div>}
    </div>
  )
}

export function Panel({ title, children, footnote }: { title: string; children: ReactNode; footnote?: string }) {
  return (
    <section className="border border-line bg-card p-4 shadow-[0_1px_1px_rgba(17,24,39,0.04)]">
      <h3 className="mb-3 text-[11px] font-medium tracking-wide text-muted">{title}</h3>
      {children}
      {footnote && <p className="mt-3 text-[11px] leading-relaxed text-muted">{footnote}</p>}
    </section>
  )
}
