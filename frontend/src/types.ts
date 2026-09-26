export type SimParams = {
  crash_magnitude: number
  crash_pct: number
  volatility: string
  liquidity: string
  n_traders: number
  avg_leverage: number
  long_ratio: number
  long_pct: number
  short_pct: number
  horizon_minutes: number
}

export type Candle = { t: number; open: number; high: number; low: number; close: number }

export type Overview = {
  simulated: boolean
  params: SimParams
  kpis: {
    current_price: number
    price_change_pct: number
    volatility: string
    volume_change_pct: number
    total_positions: number
    positions_at_risk: number
    estimated_liquidations: number
    cascade_risk: number
  }
  market: {
    primary_asset: string
    current_price: number
    starting_price: number
    price_change_pct: number
    volume: number
    volume_change_pct: number
    volatility: string
    volatility_vs_baseline: number
    liquidity: string
    liquidity_score: number
    crash_severity: string
    crash_mode: boolean
    market_state: string
    horizon_minutes: number
    candles: Candle[]
    asset_prices: Record<string, number>
    usd_inr: number
    data_label: string
  }
}

export type PositionRow = {
  trader_id: string
  asset: string
  side: string
  entry_price: number
  current_price: number
  quantity: number
  leverage: number
  initial_margin_usd: number
  unrealized_pnl_usd: number
  liquidation_price: number
  distance_to_liquidation_pct: number
  status: string
}

export type Cascade = {
  cascade_risk_score: number
  classification: string
  model_note: string
  not_a_forecast: boolean
  features: Record<string, string>
  why: string
  stages: {
    id: string
    title: string
    positions: number
    exposure_usd: number
    risk_contribution: number
    detail: string
  }[]
}

export type Exposure = {
  total_usd: number
  long_usd: number
  short_usd: number
  net_usd: number
  gross_usd: number
  liquidation_usd: number
  at_risk_usd: number
  approaching_liq_usd: number
  estimated_loss_usd: number
  by_leverage: Record<string, number>
  by_asset: {
    asset: string
    long_usd: number
    short_usd: number
    net_usd: number
    at_risk_usd: number
    liquidation_usd: number
  }[]
  usd_inr: number
}

export type MonteCarlo = {
  n_simulations: number
  average_liquidations: number
  median_liquidations: number
  worst_case_liquidations: number
  average_exposure_usd: number
  max_exposure_usd: number
  average_loss_usd: number
  severe_cascade_frequency: number
  severe_threshold_liquidations: number
  label: string
  disclaimer: string
  paths_sample: number[][]
  median_path: number[]
  severe_path: number[]
  start_price: number
  price_hist: { centers: number[]; counts: number[] }
  liquidation_hist: { centers: number[]; counts: number[] }
  loss_hist_usd_m: { centers: number[]; counts: number[] }
  exposure_hist_usd_m: { centers: number[]; counts: number[] }
  usd_inr: number
}

export type Anomaly = {
  severity: string
  time: string
  asset: string
  code: string
  description: string
  simulated: boolean
}

export type RiskSummary = {
  current_risk_level: string
  cascade_score: number
  reasons: string[]
  proposed_actions: string[]
  actions_label: string
  why: string
  severe_mc_frequency: number
}

export type LiqSummary = {
  total: number
  safe: number
  at_risk: number
  near_liquidation: number
  liquidated: number
  positions_at_risk: number
  avg_leverage: number
  long_pct: number
  short_pct: number
  leverage_histogram: Record<string, number>
  usd_inr: number
}
