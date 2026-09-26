import { NavLink, Outlet } from 'react-router-dom'
import { useSim } from '../context/SimContext'
import { SimControls } from './SimControls'
import { DataStatus } from './DataStatus'

const NAV = [
  { to: '/analyst/overview', label: 'Overview' },
  { to: '/analyst/market-crash', label: 'Market Crash' },
  { to: '/analyst/liquidations', label: 'Liquidation Monitor' },
  { to: '/analyst/cascade', label: 'AI Cascade Risk' },
  { to: '/analyst/monte-carlo', label: 'Monte Carlo' },
  { to: '/analyst/exposure', label: 'Exposure' },
  { to: '/analyst/risk-response', label: 'Risk Response' },
]

export function Layout() {
  const { overview, demoLabel, startDemo, reset, demoRunning, loading } = useSim()
  const crashMode = overview?.market.crash_mode

  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="sticky top-0 z-20 border-b border-line bg-nav text-white">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5">
          <div>
            <div className="text-[11px] tracking-[0.14em] text-white/50">P2 RISK ENGINE</div>
            <div className="text-sm font-medium">Market Crash &amp; Liquidation Intelligence</div>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span className="border border-white/20 px-2 py-0.5 text-white/80">SIMULATION MODE</span>
            <span className="border border-white/15 px-2 py-0.5 text-white/55">
              Historical/Public Data + Synthetic Portfolio
            </span>
            {crashMode ? (
              <span className="border border-[#b44a4a]/50 bg-[#b44a4a]/20 px-2 py-0.5 text-[#f3d4d4]">
                CRASH MODE
              </span>
            ) : (
              <span className="border border-white/15 px-2 py-0.5 text-white/55">MARKET NORMAL</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <a href="/" className="border border-white/25 px-3 py-1.5 text-[12px] hover:bg-white/10">Incident console</a>
            <button
              type="button"
              onClick={startDemo}
              disabled={demoRunning}
              className="border border-white/25 bg-white/5 px-3 py-1.5 text-[12px] hover:bg-white/10 disabled:opacity-40"
            >
              {demoRunning ? 'Running…' : 'Start crash simulation'}
            </button>
            <button
              type="button"
              onClick={() => void reset()}
              className="border border-white/25 px-3 py-1.5 text-[12px] hover:bg-white/10"
            >
              Reset simulation
            </button>
          </div>
        </div>
        {demoLabel && (
          <div className="border-t border-white/10 px-4 py-1 text-[11px] text-white/70">{demoLabel}</div>
        )}
      </header>

      <div className="flex min-h-[calc(100vh-52px)]">
        <aside className="hidden w-52 shrink-0 border-r border-line bg-white md:block">
          <nav className="sticky top-[52px] flex flex-col py-3 text-[13px]">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/analyst/overview'}
                className={({ isActive }) =>
                  `border-l-2 px-4 py-2 ${
                    isActive
                      ? 'border-navy bg-[#f3f4f6] font-medium text-ink'
                      : 'border-transparent text-muted hover:bg-[#fafafa]'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="px-3 pb-4">
            <DataStatus />
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex gap-1 overflow-x-auto border-b border-line bg-white px-2 py-1 text-[12px] md:hidden">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/analyst/overview'}
                className={({ isActive }) =>
                  `whitespace-nowrap px-2 py-1 ${isActive ? 'font-medium text-navy' : 'text-muted'}`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <SimControls />
          {loading && !overview ? (
            <div className="p-8 text-sm text-muted">Loading simulation engine…</div>
          ) : (
            <main className="flex-1 p-4 md:p-6">
              <Outlet />
            </main>
          )}
          <footer className="border-t border-line px-4 py-3 text-[11px] leading-relaxed text-muted">
            Research simulation only. Positions and liquidation outcomes are synthetic unless explicitly marked as
            historical/public market data. Monte Carlo outputs are scenario-based stress tests and are not forecasts.
            AI cascade scores are risk indicators, not guarantees of future market behavior.
          </footer>
        </div>
      </div>
    </div>
  )
}
