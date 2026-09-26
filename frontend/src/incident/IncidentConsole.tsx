import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useIncident } from './useIncident'
import { shortcutFor } from './shortcuts'
import { Toasts } from './Toasts'
import type { ActionQueueItem } from './types'
import type { ViewRole } from './components/RoleSwitcher'
import { SeverityBanner } from './components/SeverityBanner'
import { LiquidationInvestigator } from './components/LiquidationInvestigator'
import { DetailsDrawer } from './layout/DetailsDrawer'
import { isDetailsTab, normalizeDetailsTab, type DetailsTab } from './layout/detailsTabs'
import { MainColumns } from './layout/MainColumns'

const DETAILS_STORAGE_KEY = 'incident-details-tab'

function initialRole(): ViewRole {
  try {
    const value = localStorage.getItem('incident-role')
    if (value === 'All' || value === 'IC' || value === 'TL' || value === 'CS') return value
  } catch { /* Private browsing may disallow storage. */ }
  return 'All'
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
  const [investigating, setInvestigating] = useState(false)
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
      window.history.replaceState(null, '', url)
    } catch { /* Deep links are best-effort. */ }
  }, [details.open, details.tab])

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
  if (!state) return <main className="min-h-screen bg-bg p-8 text-sm text-muted"><h1 className="text-base font-bold text-ink">Flash-crash incident console</h1><p className="mt-3">{error ? 'Unable to load incident state.' : 'Loading incident state…'}</p><Toasts error={error} onDismiss={actions.clearError} /></main>
  const command = state.command ?? null
  const briefLine = command
    ? `${state.classifier.verdict} (LAR ${state.classifier.lar.toFixed(1)}) · ${command.first_priority} — Next: ${command.next_step}`
    : state.classifier.explanation
  const flaggedFills = command?.cluster?.flagged_count ?? 0
  const briefMe = () => {
    if (briefing) return
    setBriefing(true)
    actions.copilot({ question: 'Brief me.' }).then((reply) => speak(reply.spoken)).catch(() => {}).finally(() => setBriefing(false))
  }
  const openInvestigator = (item?: ActionQueueItem) => {
    const target = item ?? command?.queue.find((row) => row.id === 'p2.investigate')
    if (target) {
      void actions.recordQueueEvent(target.id, { actor: 'TL', event: 'opened' }).then(() => setInvestigating(true)).catch(() => {})
      return
    }
    setInvestigating(true)
  }
  return <div className="flex h-screen flex-col overflow-hidden bg-bg text-ink">
    <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-line bg-white px-4 py-2 md:px-6"><div><div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">MochaTrade / Operations</div><h1 className="text-base font-bold tracking-tight">Flash-crash incident console</h1></div><div className="flex gap-2">{state.severity.state === 'RESOLVED' && <Link to={`/summary${mock ? '?mock=1' : ''}`} className="bg-navy px-3 py-1.5 text-xs font-semibold text-white">View summary ↗</Link>}<Link to="/analyst/overview" className="border border-line px-3 py-1.5 text-xs font-semibold text-navy hover:bg-slate-50">Open analyst views ↗</Link></div></header>
    <SeverityBanner state={state} scenarios={scenarios} actions={actions} busy={busy} mock={mock} stale={stale}
      briefLine={briefLine} flaggedFills={flaggedFills} briefing={briefing} onBriefMe={briefMe} onOpenDetails={openDetails} />
    <Toasts error={error} onDismiss={actions.clearError} />
    <MainColumns state={state} command={command} role={role} busy={busy} actions={actions} onRoleChange={changeRole} onOpenDetails={openDetails} />
    {details.open && <DetailsDrawer tab={details.tab} onTabChange={(tab) => setDetails({ open: true, tab })} onClose={closeDetails}
      state={state} command={command} role={role} busy={busy} mock={mock} summary={summary} actions={actions}
      onOpenInvestigator={() => openInvestigator()} />}
    {investigating && command?.cluster && <LiquidationInvestigator cluster={command.cluster} busy={busy} onClose={() => setInvestigating(false)} onDecision={(id, decision) => void actions.decideExecution(id, { decision, actor: 'TL' }).catch(() => {})} />}
    {mock && <div className="fixed bottom-3 left-3 z-30 flex items-center gap-2 border border-amber-400 bg-amber-50 px-2 py-1.5 text-[11px] shadow"><span>Sample fixture mode</span><button type="button" onClick={() => void actions.nextFixture()} className="font-semibold text-navy underline">Next fixture</button><button type="button" onClick={() => void actions.inject({ event: 'stablecoin_dip' })} className="font-semibold text-navy underline">Emergency fixture</button></div>}
    <button type="button" className="fixed bottom-3 right-3 z-30 border border-line bg-white px-2 py-1 text-xs font-bold shadow" onClick={() => setHelp(true)} aria-label="Keyboard shortcuts">?</button>
    {help && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setHelp(false) }}><div role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" className="w-full max-w-sm bg-white p-5 text-sm shadow-xl"><h2 className="font-bold">Keyboard shortcuts</h2><p className="mt-3 leading-7">1 IC · 2 TL · 3 CS · 0 All<br />A approve top action · S skip top action<br />N add a note · Space pause or resume · D details drawer<br />? show shortcuts · Esc close</p><button type="button" onClick={() => setHelp(false)} className="mt-4 border border-line px-3 py-1.5 text-xs font-semibold">Close</button></div></div>}
  </div>
}
