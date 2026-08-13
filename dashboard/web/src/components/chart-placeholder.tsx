import { CartesianGrid, LineChart, ResponsiveContainer } from "recharts"

export function ChartPlaceholder() {
  return (
    <div className="chart-placeholder" aria-label="Metrics source unavailable">
      <ResponsiveContainer width="100%" height={176}>
        <LineChart data={[]} margin={{ top: 12, right: 8, bottom: 12, left: 8 }}>
          <CartesianGrid stroke="currentColor" strokeDasharray="3 7" vertical={false} />
        </LineChart>
      </ResponsiveContainer>
      <div className="chart-placeholder-copy">
        <span className="status-dot status-neutral" />
        <strong>No verified metric series</strong>
        <span>No metric source is connected.</span>
      </div>
    </div>
  )
}
