import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Candle } from '../types'

export function PriceChart({ candles, height = 260 }: { candles: Candle[]; height?: number }) {
  const data = candles.map((c) => ({ t: c.t, close: c.close, high: c.high, low: c.low }))
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#6B7280' }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fontSize: 10, fill: '#6B7280' }}
            axisLine={{ stroke: '#E5E7EB' }}
            tickLine={false}
            width={52}
          />
          <Tooltip
            contentStyle={{ border: '1px solid #E5E7EB', fontSize: 12, borderRadius: 2 }}
            formatter={(v) => [`$${Number(v).toFixed(2)}`, 'Close']}
          />
          <Line type="monotone" dataKey="close" stroke="#334E68" strokeWidth={1.6} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
