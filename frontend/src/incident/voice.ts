/** H15: shared voice utilities for the severity banner's "Brief me" and the copilot dock. */

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
