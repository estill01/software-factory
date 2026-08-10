import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts"

export type MetricTrendPoint = {
  date: string
  activity: number
  incidents: number
  estimatedTokens: number
  sources: MetricTrendSource[]
}

export type MetricTrendSource = {
  targetThreadId: string
  targetLabel: string
  metricId: string
  sourceRoot: string
  firstRecordId: string | null
  lastRecordId: string | null
}

export function MetricHistoryChart({ points }: { points: MetricTrendPoint[] }) {
  return (
    <div
      className="report-trend-chart"
      role="img"
      aria-label="Recorded activity and incident trend. Exact values are available in the adjacent table."
    >
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={points} margin={{ top: 12, right: 14, bottom: 4, left: -18 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 6" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--text-faint)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "var(--text-faint)", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Line
            type="monotone"
            dataKey="activity"
            name="Recorded activity"
            stroke="var(--primary-bright)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="incidents"
            name="Incidents opened"
            stroke="var(--red)"
            strokeWidth={1.8}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
