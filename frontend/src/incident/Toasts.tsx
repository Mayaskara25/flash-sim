export function Toasts({ error, onDismiss }: { error: string | null; onDismiss: () => void }) {
  if (!error) return null
  return <div role="alert" className="fixed bottom-4 right-4 z-50 flex max-w-md items-start gap-3 border border-red-300 bg-red-50 p-3 text-sm text-red-950 shadow-lg">
    <span>{error}</span><button type="button" className="font-semibold underline" onClick={onDismiss}>Dismiss</button>
  </div>
}
