import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { SimProvider } from './context/SimContext'
import { CascadeRiskPage } from './pages/CascadeRisk'
import { ExposurePage } from './pages/Exposure'
import { LiquidationMonitorPage } from './pages/LiquidationMonitor'
import { MarketCrashPage } from './pages/MarketCrash'
import { MonteCarloPage } from './pages/MonteCarlo'
import { OverviewPage } from './pages/Overview'
import { RiskResponsePage } from './pages/RiskResponse'
import { IncidentConsole } from './incident/IncidentConsole'
import { IncidentSummaryPage } from './incident/IncidentSummaryPage'
import { UiKit } from './incident/UiKit'

export default function App() {
  return (
    <SimProvider>
      <BrowserRouter>
        <Routes>
          <Route index element={<IncidentConsole />} />
          <Route path="ui-kit" element={<UiKit />} />
          <Route path="summary" element={<IncidentSummaryPage />} />
          <Route path="analyst" element={<Layout />}>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<OverviewPage />} />
            <Route path="market-crash" element={<MarketCrashPage />} />
            <Route path="liquidations" element={<LiquidationMonitorPage />} />
            <Route path="cascade" element={<CascadeRiskPage />} />
            <Route path="monte-carlo" element={<MonteCarloPage />} />
            <Route path="exposure" element={<ExposurePage />} />
            <Route path="risk-response" element={<RiskResponsePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </SimProvider>
  )
}
