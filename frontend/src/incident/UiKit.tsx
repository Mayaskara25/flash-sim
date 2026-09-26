import { useState } from 'react'
import { fmtClock, fmtInt, fmtPct, tagFullName, tagName } from './format'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Panel } from './ui/Panel'
import { Stat } from './ui/Stat'
import { Tag } from './ui/Tag'

type Theme = 'system' | 'light' | 'dark'

/** H13 dev-only kitchen sink: every primitive in every tone, light + dark. */
export function UiKit() {
  const [theme, setTheme] = useState<Theme>('system')
  const cycle = () => {
    const next: Theme = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system'
    setTheme(next)
    if (next === 'system') delete document.documentElement.dataset.theme
    else document.documentElement.dataset.theme = next
  }
  return (
    <main
      className="text-body"
      style={{ background: 'var(--bg)', color: 'var(--ink)', minHeight: '100vh', padding: 24, maxWidth: 1100, margin: '0 auto' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div className="text-label" style={{ color: 'var(--muted)' }}>
            H13 · Design tokens
          </div>
          <h1 className="text-headline" style={{ margin: '4px 0 0' }}>
            UI kit
          </h1>
          <p className="text-body-lg" style={{ color: 'var(--muted)', margin: '8px 0 0' }}>
            Projector scale (≥12px), severity colours, and the five H14 primitives. Nothing here is wired to
            incident state.
          </p>
        </div>
        <Button variant="secondary" size="md" onClick={cycle}>
          Theme: {theme} — switch
        </Button>
      </div>

      <div style={{ display: 'grid', gap: 16, marginTop: 24 }}>
        <Panel title="Type scale" action={<Badge tone="sev4">≥ 12px</Badge>}>
          <div style={{ display: 'grid', gap: 8 }}>
            <span className="text-label">Label · 12px semibold uppercase — eyebrows, field names</span>
            <span className="text-body">Body · 14px — default copy, log lines, drafts</span>
            <span className="text-body-lg">Body large · 16px — action text, briefs</span>
            <span className="text-stat">28px mono — 410/min</span>
            <span className="text-headline">32px — SEV-2 Critical</span>
          </div>
        </Panel>

        <Panel title="Stat — every status">
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <Stat label="Liq rate" value="410" unit="/min" status="critical" trend="↗ rising fast" />
            <Stat label="Ins fund" value="40" unit="%" status="warn" trend="↘ −4 %/min" />
            <Stat label="Price 5m" value="−9.8" unit="%" status="warn" trend="↘ falling" />
            <Stat label="Tickets" value="4.3" unit="×" status="warn" trend="↗ 4× baseline" />
            <Stat label="Engine health" value="OK" status="ok" trend="→ steady" />
            <Stat label="Latency" value="180" unit="ms" status="watch" trend="→ watching" />
          </div>
        </Panel>

        <Panel title="Badge — every tone (text, never colour alone)">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Badge tone="sev1">SEV-1 · Emergency</Badge>
            <Badge tone="sev2">SEV-2 · Critical</Badge>
            <Badge tone="sev3">SEV-3 · Warning</Badge>
            <Badge tone="sev4">SEV-4 · Normal</Badge>
            <Badge tone="ok">OK · settled</Badge>
            <Badge tone="warn">Warn · watch</Badge>
            <Badge tone="crit">Crit · act now</Badge>
            <Badge tone="neutral">Neutral</Badge>
          </div>
        </Panel>

        <Panel title="Button — variants × sizes">
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <Button variant="primary" size="lg">
              Approve reduce-only
            </Button>
            <Button variant="primary" size="md">
              Primary md
            </Button>
            <Button variant="secondary" size="md">
              Secondary
            </Button>
            <Button variant="ghost" size="md">
              Skip
            </Button>
            <Button variant="primary" size="md" loading>
              Approving
            </Button>
            <Button variant="secondary" size="md" disabled>
              Disabled
            </Button>
          </div>
        </Panel>

        <Panel title="Tag — code + short name, full name on hover">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <Tag code="M1" />
            <Tag code="M2" />
            <Tag code="I1" />
            <Tag code="P3" />
            <Tag code="S1" active={false} />
            <Tag code="R2" active={false} />
          </div>
          <p className="text-body" style={{ color: 'var(--muted)', marginTop: 12 }}>
            Hover a tag: “{tagName('M2')}” expands to “{tagFullName('M2')}”.
          </p>
        </Panel>

        <Panel title="format.ts helpers">
          <div className="text-body" style={{ display: 'grid', gap: 6 }}>
            <span>
              fmtInt(12345) → <strong>{fmtInt(12345)}</strong>
            </span>
            <span>
              fmtPct(9.84) → <strong>{fmtPct(9.84)}</strong>
            </span>
            <span>
              fmtClock(872) → <strong>{fmtClock(872)}</strong>
            </span>
            <span>
              tagName(&quot;M2&quot;) → <strong>{tagName('M2')}</strong>
            </span>
          </div>
        </Panel>
      </div>
    </main>
  )
}
