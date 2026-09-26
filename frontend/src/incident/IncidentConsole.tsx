import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Toasts } from './Toasts'
import { useIncident } from './useIncident'
import { shortcutFor } from './shortcuts'
import type { ActionQueueItem } from './types'
import type { ViewRole } from './components/RoleSwitcher'
import { SeverityBanner } from './components/SeverityBanner'
import { DetailsDrawer } from './layout/DetailsDrawer'
import { isDetailsTab, normalizeDetailsTab, type DetailsTab } from './layout/detailsTabs'
import { MainColumns } from './layout/MainColumns'

const DETAILS_STORAGE_KEY = 'incident-details-tab'

/**
 * H14: the default view is **IC**, not "All".
 *
 * "All" showed every role's cards at once, which put three competing
 * headlines on the screen and buried the IC's own top action (H12/H13 review
 * finding 2). IC is the role that owns the primary action, so it is what a
 * stranger sees first. `?role=All` deep-links the other views (QA, rehearsal
 * links) and the choice is remembered per browser.
 */
function initialRole(): ViewRole {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get('role')
    if (fromUrl === 'All' || fromUrl === 'IC' || fromUrl === 'TL' || fromUrl === 'CS') return fromUrl
  } catch { /* Deep links are best-effort. */ }
  try {
    const value = localStorage.getItem('incident-role')
    if (value === 'All' || value === 'IC' || value === 'TL' || value === 'CS') return value
  } catch { /* Private browsing may disallow storage. */ }
  return 'IC'
}

function initialDetails(): { open: boolean; tab: DetailsTab } {
  let remembered: DetailsTab = 'signals'
  try {
    const value = localStorage.getItem(DETAILS_STORAGE_KEY)
    if (isDetailsTab(value)) remembered = value
  } catch { /* Optional preference. */ }
  try {
    const tab = normalizeDetailsTab(new URLSearchParams(window.location.search).get('details'))
    if (tab) return { open: true, tab }
  } catch { /* Keep the remembered tab when the URL is unreadable. */ }
  return { open: false, tab: remembered }
}

function speak(text: string) {
  try {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
  } catch { /* Voice output is best-effort. */ }
}

export function IncidentConsole() {
  const incident = useIncident()
  const { state, actions, busy, mock, stale, error, scenarios, summary } = incident
  const [role, setRole] = useState<ViewRole>(initialRole)
  const [help, setHelp] = useState(false)
  const [details, setDetails] = useState(initialDetails)
  const [briefing, setBriefing] = useState(false)
  const changeRole = (value: ViewRole) => { setRole(value); try { localStorage.setItem('incident-role', value) } catch { /* Optional preference. */ } }
  const openDetails = (tab?: DetailsTab) => setDetails((current) => ({ open: true, tab: tab ?? current.tab }))
  const closeDetails = () => setDetails((current) => ({ ...current, open: false }))
  const onOpenNotes = () => { openDetails('log'); window.setTimeout(() => document.getElementById('incident-note')?.focus(), 50) }

  useEffect(() => {
    try { localStorage.setItem(DETAILS_STORAGE_KEY, details.tab) } catch { /* Optional preference. */ }
    try {
      const url = new URL(window.location.href)
      if (details.open) url.searchParams.set('details', details.tab)
      else url.searchParams.delete('details')
      url.searchParams.set('role', role)
      window.history.replaceState(null, '', url)
    } catch { /* Deep links are best-effort. */ }
  }, [details.open, details.tab, role])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && details.open) { setDetails((current) => ({ ...current, open: false })); return }
      if (help && event.key === 'Escape') { setHelp(false); return }
      if (help) return
      const target = event.target
      const typing = target instanceof HTMLElement && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.closest('[role="dialog"]'))
      if (!typing && (event.key === 'd' || event.key === 'D') && !event.altKey && !event.ctrlKey && !event.metaKey) { event.preventDefault(); setDetails((current) => ({ open: !current.open, tab: current.tab })); return }
      if (typing) return
      const shortcut = shortcutFor(event)
      if (!shortcut) return
      if (shortcut === 'IC' || shortcut === 'TL' || shortcut === 'CS' || shortcut === 'All') changeRole(shortcut)
      else if (shortcut === 'help') setHelp(true)
      else if (shortcut === 'note') { event.preventDefault(); onOpenNotes() }
      else if (shortcut === 'clock' && state?.sim.started && !busy) { event.preventDefault(); void actions.clock({ op: state.sim.running ? 'pause' : 'resume' }).catch(() => {}) }
      else if ((shortcut === 'approve' || shortcut === 'skip') && !busy) { event.preventDefault(); window.dispatchEvent(new CustomEvent('incident-action-shortcut', { detail: shortcut })) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [actions, busy, help, details.open, state?.sim.running, state?.sim.started])

  if (!state) return <main className="min-h-screen bg-bg p-8 text-body text-muted"><h1 className="text-body-lg font-bold text-ink">MochaTrade Ops Console</h1><p className="mt-3">{error ? 'Unable to load incident state.' : 'Loading incident state…'}</p><Toasts error={error} onDismiss={actions.clearError} /></main>

  const command = state.command ?? null
  // Banner row 2: the one-line brief. The backend brief already names the
  // verdict and the LAR, so the console does not prefix them again. The
  // action to take is the hero card below, not repeated here (UI_PLAN rule 6).
  const briefLine = command ? command.why_first : state.classifier.explanation
  const flaggedFills = command?.cluster?.flagged_count ?? 0
  const briefMe = () => {
    if (briefing) return
    setBriefing(true)
    actions.copilot({ question: 'Brief me.' }).then((reply) => speak(reply.spoken)).catch(() => {}).finally(() => setBriefing(false))
  }
  // Command-queue cards that are not playbook actions. "OPEN" on the cluster
  // card records the investigation event; "RUN" runs the modelled stress test.
  const onQueueAction = (item: ActionQueueItem) => {
    if (item.button === 'OPEN' && item.ref?.startsWith('LC-')) {
      void actions.recordQueueEvent(item.id, { actor: 'TL', event: 'opened' }).catch(() => {})
      return
    }
    void actions.recordQueueEvent(item.id, { actor: 'TL', event: 'run' }).catch(() => {})
  }

  return <div className="flex h-screen flex-col overflow-hidden bg-bg text-ink">
    <SeverityBanner state={state} scenarios={scenarios} actions={actions} busy={busy} mock={mock} stale={stale}
      briefLine={briefLine} flaggedFills={flaggedFills} briefing={briefing} onBriefMe={briefMe} onOpenDetails={openDetails} onHelp={() => setHelp(true)} />
    <Toasts error={error} onDismiss={actions.clearError} />
    <MainColumns state={state} command={command} role={role} busy={busy} actions={actions} onRoleChange={changeRole} onOpenDetails={openDetails} onQueueAction={onQueueAction} />
    {details.open && <DetailsDrawer tab={details.tab} onTabChange={(tab) => setDetails({ open: true, tab })} onClose={closeDetails}
      state={state} command={command} role={role} busy={busy} mock={mock} summary={summary} actions={actions}
      onOpenInvestigator={() => {
        const target = command?.queue.find((row) => row.id === 'p2.investigate')
        if (target) void actions.recordQueueEvent(target.id, { actor: 'TL', event: 'opened' }).catch(() => {})
      }} />}
    {mock && <div className="fixed bottom-3 left-3 z-30 flex items-center gap-2 border px-2 py-1.5 text-xs shadow" style={{ borderColor: 'var(--warn-border)', background: 'var(--warn-bg)', color: 'var(--warn-fg)' }}><span>Sample fixture mode</span><button type="button" onClick={() => void actions.nextFixture()} className="font-semibold underline">Next fixture</button><button type="button" onClick={() => void actions.inject({ event: 'stablecoin_dip' })} className="font-semibold underline">Emergency fixture</button></div>}
    {help && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setHelp(false) }}>
      <div role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" className="w-full max-w-sm p-5 text-body shadow-xl" style={{ background: 'var(--surface)' }}>
        <h2 className="text-body-lg font-bold">Keyboard shortcuts</h2>
        <p className="text-body mt-3 leading-7">1 IC · 2 TL · 3 CS · 0 All<br />A approve top action · S skip top action<br />N add a note · Space pause or resume · D details drawer<br />? show shortcuts · Esc close</p>
        <button type="button" onClick={() => setHelp(false)} className="text-body mt-4 border px-3 py-1.5 font-semibold" style={{ borderColor: 'var(--line)' }}>Close</button>
      </div>
    </div>}
    <nav className="flex shrink-0 items-center gap-2 border-t px-4 py-1.5 md:px-6" style={{ borderColor: 'var(--line)', background: 'var(--surface)' }} aria-label="Other views">
      <span className="text-label" style={{ color: 'var(--muted)' }}>MochaTrade Ops Console</span>
      {state.severity.state === 'RESOLVED' && <Link to={`/summary${mock ? '?mock=1' : ''}`} className="text-body font-semibold underline underline-offset-2" style={{ color: 'var(--ink)' }}>View incident summary ↗</Link>}
      <Link to="/analyst/overview" className="text-body font-semibold underline underline-offset-2" style={{ color: 'var(--ink)' }}>Analyst views ↗</Link>
    </nav>
  </div>
}
