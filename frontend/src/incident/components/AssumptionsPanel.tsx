import { useState } from 'react'

const assumptions = [
  'MochaTrade model: INR via UPI → USDT/USDC custodial wallet → leveraged futures and options; mixed A-book/B-book hedging.',
  'All thresholds, weights and baselines are simulation values, not MochaTrade production figures.',
  'Insurance fund exists and starts at a fixed simulated amount.',
  'Three roles: Incident Commander, Tech Lead, Comms/Support lead.',
  'Signals are simulated; real exchange feeds, ticketing and social listening are outside this demo.',
  'Protective controls are proposed by the tool and executed only on human approval.',
  'Regulatory handling (R2) is escalated to founders; the tool only flags and records it.',
]

export function AssumptionsPanel() {
  const [open, setOpen] = useState(false)
  return <>
    <button type="button" onClick={() => setOpen(true)} className="whitespace-nowrap text-xs border border-white/35 px-1.5 py-0.5 underline">Assumptions</button>
    {open && <div className="fixed inset-0 z-50 bg-slate-950/50" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false) }}>
      <aside role="dialog" aria-modal="true" aria-label="Simulation assumptions" className="ml-auto h-full w-full max-w-md overflow-y-auto bg-card p-5 text-ink shadow-xl">
        <div className="flex items-start justify-between gap-3"><div><h2 className="text-lg font-bold">Demo assumptions</h2><p className="mt-1 text-xs text-muted">Read these before the incident walkthrough.</p></div><button type="button" onClick={() => setOpen(false)} className="border border-slate-300 px-2 py-1 text-xs">Close</button></div>
        <ol className="mt-5 list-decimal space-y-3 pl-5 text-sm leading-relaxed">{assumptions.map((item) => <li key={item}>{item}</li>)}</ol>
        <p className="mt-5 border-l-2 border-amber-500 bg-amber-50 p-3 text-xs">Forecasts are simulated projections, not market forecasts or production risk estimates.</p>
      </aside>
    </div>}
  </>
}
