import { useEffect, useRef, useState } from 'react'
import type { CopilotReply, IncidentStateDTO } from '../types'
import { hasSpeechRecognition, speak, speechRecognitionConstructor, stopSpeaking, useSpeaking, type SpeechRecognitionInstance } from '../voice'

const ANNOUNCE_KEY = 'incident-announce-escalations'
const ANNOUNCE_THROTTLE_MS = 20_000

/**
 * H15: floating "Ask copilot" dock, replacing the old always-open Copilot
 * details tab. Stays out of the way until asked; can optionally speak one
 * short line on an upward severity transition (default off).
 */
export function CopilotDock({ state, onAsk }: {
  state: IncidentStateDTO
  onAsk: (question: string) => Promise<CopilotReply>
}) {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [reply, setReply] = useState<CopilotReply | null>(null)
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const [announce, setAnnounce] = useState(() => {
    try { return localStorage.getItem(ANNOUNCE_KEY) === '1' } catch { return false }
  })
  const recognition = useRef<SpeechRecognitionInstance | null>(null)
  const voiceAvailable = hasSpeechRecognition()

  const lastSev = useRef<number | null>(null)
  const lastAnnounceAt = useRef(0)

  useEffect(() => {
    try { localStorage.setItem(ANNOUNCE_KEY, announce ? '1' : '0') } catch { /* Optional preference. */ }
  }, [announce])

  // Announce escalations: speak one short line on an upward transition
  // (lower SEV number = worse), throttled to at most once per 20s.
  useEffect(() => {
    const sev = state.severity.sev
    const previous = lastSev.current
    lastSev.current = sev
    if (previous === null || sev >= previous || !announce) return
    const now = Date.now()
    if (now - lastAnnounceAt.current < ANNOUNCE_THROTTLE_MS) return
    lastAnnounceAt.current = now
    const rate = state.command?.liquidation_rate
    const next = state.command?.next_step
    const parts = [`Severity ${sev}, ${state.severity.state.toLowerCase()}.`]
    if (rate != null) parts.push(`Liquidations ${rate.toFixed(0)} per minute.`)
    if (next) parts.push(`Recommended: ${next}`)
    speak(parts.join(' '))
  }, [state.severity.sev, state.severity.state, state.command, announce])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') { event.stopPropagation(); stopSpeaking(); setOpen(false) } }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [open])

  // Esc stops speech anywhere on the console, even with the dock closed
  // (the banner's "Brief me" also speaks).
  const speaking = useSpeaking()
  useEffect(() => {
    if (!speaking) return
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') stopSpeaking() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [speaking])

  const ask = async (value: string, play = false) => {
    if (!value.trim() || busy) return
    setBusy(true); setError('')
    try {
      const response = await onAsk(value.trim())
      setReply(response)
      if (play) speak(response.spoken)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to prepare the briefing.') }
    finally { setBusy(false) }
  }

  const startVoice = () => {
    const Constructor = speechRecognitionConstructor()
    if (!Constructor) return
    setError(''); setListening(true)
    const instance = new Constructor()
    recognition.current = instance
    instance.lang = 'en-IN'; instance.interimResults = false; instance.maxAlternatives = 1
    instance.onresult = (event) => { const transcript = event.results[0]?.[0]?.transcript ?? ''; setQuestion(transcript); void ask(transcript, true) }
    instance.onerror = () => { setError('Voice input could not be captured. Try again or type your question.'); setListening(false) }
    instance.onend = () => setListening(false)
    instance.start()
  }

  return <>
    {speaking && <button type="button" onClick={stopSpeaking} aria-label="Stop voice"
      className="fixed bottom-16 right-44 z-40 border border-red-700 bg-red-700 px-3 py-1.5 text-sm font-bold text-white shadow-lg">■ Stop voice</button>}
    <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-label="Ask copilot"
      className="fixed bottom-16 right-3 z-30 bg-navy px-3 py-2 text-xs font-bold text-white shadow-lg hover:bg-navy/90">
      🎙 Ask copilot
    </button>
    {open && <aside role="dialog" aria-modal="false" aria-label="AI incident copilot"
      className="fixed bottom-28 right-3 z-40 flex max-h-[70vh] w-[400px] max-w-[92vw] flex-col overflow-y-auto border border-line bg-white p-3 shadow-2xl md:p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-[0.13em]">AI incident copilot</h2>
          <p className="mt-1 text-xs text-muted">Operational assistant. Responses are generated from the current modelled incident state; it cannot execute controls.</p>
        </div>
        <button type="button" onClick={() => setOpen(false)} aria-label="Close copilot (Esc)" className="border border-line px-2 py-1 text-xs font-semibold">✕</button>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1.5">
          <button type="button" disabled={busy} onClick={() => void ask('Brief me.', true)} className="bg-navy px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50">🎙 Brief me</button>
          {voiceAvailable
            ? <button type="button" disabled={busy || listening} onClick={startVoice} className="border border-navy px-2.5 py-1.5 text-xs font-semibold text-navy disabled:opacity-50">🎤 {listening ? 'Listening…' : 'Ask'}</button>
            : <span title="Voice input is unavailable in this browser (e.g. Firefox). You can still type a question." className="border border-line px-2.5 py-1.5 text-xs font-semibold text-muted">🎤 Ask (unavailable)</span>}
        </div>
        <label className="flex items-center gap-1.5 text-xs text-muted" title="Speak one short line when severity gets worse, at most once per 20s">
          <input type="checkbox" checked={announce} onChange={(event) => setAnnounce(event.target.checked)} />
          Announce escalations
        </label>
      </div>
      <form className="mt-3 flex gap-2" onSubmit={(event) => { event.preventDefault(); void ask(question) }}>
        <label className="sr-only" htmlFor="p2-copilot-question">Ask copilot</label>
        <input id="p2-copilot-question" value={question} onChange={(event) => setQuestion(event.target.value)} className="min-w-0 flex-1 border border-line px-2 py-1.5 text-xs" placeholder="What should I do first? What changed? Why was this flagged?" />
        <button type="submit" disabled={busy || !question.trim()} className="border border-line px-3 py-1.5 text-xs font-semibold disabled:opacity-50">{busy ? 'Thinking…' : 'Ask'}</button>
      </form>
      {error && <p className="mt-2 text-xs text-red-800">{error}</p>}
      {reply && <div className="mt-3 border-l-2 border-navy bg-slate-50 p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Briefing</p>
          <button type="button" onClick={() => speak(reply.spoken)} className="text-xs font-semibold text-navy underline">Play response</button>
        </div>
        <p className="mt-1 text-xs leading-relaxed">{reply.answer}</p>
        <div className="mt-2 grid gap-2 text-xs md:grid-cols-3">
          <div><strong>FIRST PRIORITY</strong><p>{reply.first_priority}</p></div>
          <div><strong>WHY</strong>{reply.why.map((why) => <p key={why}>{why}</p>)}</div>
          <div><strong>NEXT</strong><p>{reply.next_step}</p></div>
        </div>
      </div>}
    </aside>}
  </>
}
