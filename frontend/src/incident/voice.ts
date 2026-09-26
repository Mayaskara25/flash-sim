/** H15: shared voice utilities for the severity banner's "Brief me" and the copilot dock. */
import { useEffect, useState } from 'react'

/** Stop any speech immediately (Stop button, Esc, closing the dock). */
export function stopSpeaking(): void {
  try { if ('speechSynthesis' in window) window.speechSynthesis.cancel() } catch { /* best-effort */ }
}

/** True while the browser is speaking; polled because speechSynthesis has no global change event. */
export function useSpeaking(): boolean {
  const [speaking, setSpeaking] = useState(false)
  useEffect(() => {
    if (!('speechSynthesis' in window)) return
    const id = window.setInterval(() => setSpeaking(window.speechSynthesis.speaking), 250)
    return () => window.clearInterval(id)
  }, [])
  return speaking
}

/** Speak `text`, cancelling any utterance already in flight. Best-effort: never throws. */
export function speak(text: string): void {
  try {
    if (!('speechSynthesis' in window) || !text.trim()) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = 1.05
    const voice = pickEnglishVoice()
    if (voice) utterance.voice = voice
    window.speechSynthesis.speak(utterance)
  } catch { /* Voice output is best-effort. */ }
}

function pickEnglishVoice(): SpeechSynthesisVoice | undefined {
  try {
    const voices = window.speechSynthesis.getVoices()
    return voices.find((voice) => voice.lang.toLowerCase().startsWith('en')) ?? voices[0]
  } catch { return undefined }
}

export type SpeechResultEvent = { results: ArrayLike<ArrayLike<{ transcript: string }>> }
export type SpeechRecognitionInstance = {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: SpeechResultEvent) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
}
export type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance

/** The constructor for browser speech-to-text, or undefined when unsupported (e.g. Firefox). */
export function speechRecognitionConstructor(): SpeechRecognitionConstructor | undefined {
  const candidate = window as Window & {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
  return candidate.SpeechRecognition ?? candidate.webkitSpeechRecognition
}

/** Whether voice "Ask" should be shown at all. */
export function hasSpeechRecognition(): boolean {
  return speechRecognitionConstructor() !== undefined
}
