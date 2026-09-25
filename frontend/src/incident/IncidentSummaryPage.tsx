import { SummaryView } from './components/SummaryView'
import { useIncident } from './useIncident'
import { FIXTURES } from './fixtures'

export function IncidentSummaryPage() {
  const incident = useIncident()
  return <SummaryView summary={incident.summary} templates={incident.mock ? FIXTURES.resolved.templates : incident.state?.templates ?? []} mock={incident.mock} />
}
