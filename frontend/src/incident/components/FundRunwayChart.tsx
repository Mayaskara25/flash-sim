import { Area, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Forecast, SignalView } from '../types'

export function FundRunwayChart({ fund, forecast, t }: { fund: SignalView | undefined; forecast: Forecast; t: number }) {
  const history = (fund?.history ?? []).map(([time, value]) => ({ minute: Number(((time - t) / 60).toFixed(1)), actual: value }))
  const projection = forecast.ins_fund.map((point) => ({ minute: point.h, base: point.p10, band: point.p90 - point.p10, median: point.p50 }))
  const data = [...history, { minute: 0, actual: fund?.value, median: fund?.value }, ...projection]
  return <div className="h-44 w-full" role="img" aria-label="Insurance fund history and simulated 15 minute p10 to p90 runway">
    <ResponsiveContainer width="100%" height="100%"><ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
      <XAxis dataKey="minute" type="number" domain={['dataMin', 'dataMax']} tick={{ fill: '#fff', fontSize: 10 }} tickFormatter={(value: number) => `${value > 0 ? '+' : ''}${value}m`} />
      <YAxis domain={[0, 100]} tick={{ fill: '#fff', fontSize: 10 }} unit="%" />
      <Tooltip contentStyle={{ color: '#172b4d', fontSize: 11 }} labelFormatter={(value) => `Offset ${value} min`} />
      <ReferenceLine y={25} stroke="#fca5a5" strokeDasharray="4 3" label={{ value: '25% threshold', position: 'insideTopRight', fill: '#fecaca', fontSize: 10 }} />
      <Area dataKey="base" stackId="range" stroke="none" fill="transparent" isAnimationActive={false} />
      <Area dataKey="band" stackId="range" stroke="none" fill="#93c5fd" fillOpacity={0.35} isAnimationActive={false} />
      <Line dataKey="actual" stroke="#fff" strokeWidth={2} dot={false} isAnimationActive={false} name="Observed" />
      <Line dataKey="median" stroke="#60a5fa" strokeWidth={2} dot isAnimationActive={false} name="Projected p50" />
    </ComposedChart></ResponsiveContainer>
  </div>
}
