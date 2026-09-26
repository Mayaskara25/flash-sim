import { useRef, useState } from 'react'
import type { CopilotReply } from '../types'

type SpeechResultEvent = { results: ArrayLike<ArrayLike<{ transcript: string }>> }
type Recognition = { lang: string; interimResults: boolean; maxAlternatives: number; onresult: ((event: SpeechResultEvent) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; start: () => void }
type RecognitionConstructor = new () => Recognition

function speak(text: string) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
}

function browserRecognition(): RecognitionConstructor | undefined {
  const candidate = window as Window & { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor }
  return candidate.SpeechRecognition ?? candidate.webkitSpeechRecognition
}

export function AICopilot({ onAsk }: { onAsk: (question: string) => Promise<CopilotReply> }) {
  const [question, setQuestion] = useState('')
  const [reply, setReply] = useState<CopilotReply | null>(null)
  const [busy, setBusy] = useState(false)
  const [listening, setListening] = useState(false)
  const [error, setError] = useState('')
  const recognition = useRef<Recognition | null>(null)

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
    const Constructor = browserRecognition()
    if (!Constructor) { setError('Voice input is unavailable in this browser. You can still type a question.'); return }
    setError(''); setListening(true)
    const instance = new Constructor()
    recognition.current = instance
    instance.lang = 'en-IN'; instance.interimResults = false; instance.maxAlternatives = 1
    instance.onresult = (event) => { const transcript = event.results[0]?.[0]?.transcript ?? ''; setQuestion(transcript); void ask(transcript, true) }
    instance.onerror = () => { setError('Voice input could not be captured. Try again or type your question.'); setListening(false) }
    instance.onend = () => setListening(false)
    instance.start()
  }
  return <section className="border border-line bg-white p-3 md:p-4" aria-label="AI incident copilot"><div className="flex flex-wrap items-start justify-between gap-2"><div><h2 className="text-xs font-bold uppercase tracking-[0.13em]">AI incident copilot</h2><p className="mt-1 text-xs text-muted">Operational assistant. Responses are generated from the current modelled incident state; it cannot execute controls.</p></div><div className="flex gap-1.5"><button type="button" disabled={busy} onClick={() => void ask('Brief me.', true)} className="bg-navy px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50">🎙 Brief me</button><button type="button" disabled={busy || listening} onClick={startVoice} className="border border-navy px-2.5 py-1.5 text-xs font-semibold text-navy disabled:opacity-50">🎤 {listening ? 'Listening…' : 'Ask'}</button></div></div><form className="mt-3 flex gap-2" onSubmit={(event) => { event.preventDefault(); void ask(question) }}><label className="sr-only" htmlFor="copilot-question">Ask the copilot</label><input id="copilot-question" value={question} onChange={(event) => setQuestion(event.target.value)} className="min-w-0 flex-1 border border-line px-2 py-1.5 text-xs" placeholder="What should I do first? What changed? Why was this flagged?" /><button type="submit" disabled={busy || !question.trim()} className="border border-line px-3 py-1.5 text-xs font-semibold disabled:opacity-50">{busy ? 'Thinking…' : 'Ask'}</button></form>{error && <p className="mt-2 text-xs text-red-800">{error}</p>}{reply && <div className="mt-3 border-l-2 border-navy bg-slate-50 p-3"><div className="flex items-center justify-between gap-2"><p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Briefing</p><button type="button" onClick={() => speak(reply.spoken)} className="text-xs font-semibold text-navy underline">Play response</button></div><p className="mt-1 text-xs leading-relaxed">{reply.answer}</p><div className="mt-2 grid gap-2 text-xs md:grid-cols-3"><div><strong>FIRST PRIORITY</strong><p>{reply.first_priority}</p></div><div><strong>WHY</strong>{reply.why.map((why) => <p key={why}>{why}</p>)}</div><div><strong>NEXT</strong><p>{reply.next_step}</p></div></div></div>}</section>
}
