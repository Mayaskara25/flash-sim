export const DETAILS_TABS = ['signals', 'liquidations', 'comms', 'log', 'report', 'copilot'] as const
export type DetailsTab = (typeof DETAILS_TABS)[number]

export const TAB_LABELS: Record<DetailsTab, string> = {
  signals: 'Signals',
  liquidations: 'Liquidations',
  comms: 'Comms',
  log: 'Log',
  report: 'Report',
  copilot: 'Copilot',
}

export function isDetailsTab(value: unknown): value is DetailsTab {
  return typeof value === 'string' && (DETAILS_TABS as readonly string[]).includes(value)
}

const ALIASES: Record<string, DetailsTab> = {
  signal: 'signals',
  liquidation: 'liquidations',
  comm: 'comms',
  comms: 'comms',
  communication: 'comms',
  communications: 'comms',
}

/** Normalise a `?details=` deep-link value to a tab, or null when absent/invalid. */
export function normalizeDetailsTab(value: string | null): DetailsTab | null {
  if (!value) return null
  const key = value.toLowerCase()
  if (isDetailsTab(key)) return key
  return ALIASES[key] ?? null
}
