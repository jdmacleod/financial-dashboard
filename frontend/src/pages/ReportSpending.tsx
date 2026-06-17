import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { reportsApi } from "@/api/reports"
import { formatCurrency } from "@/lib/formatters"
import { currentMonthRange, lastNMonthsRange } from "@/lib/dateRange"

const CHART_COLORS = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#84cc16",
]

type Preset = "this_month" | "3m" | "6m" | "12m"

function presetRange(p: Preset) {
  if (p === "this_month") return currentMonthRange()
  if (p === "3m") return lastNMonthsRange(3)
  if (p === "6m") return lastNMonthsRange(6)
  return lastNMonthsRange(12)
}

export default function ReportSpending() {
  const [preset, setPreset] = useState<Preset>("this_month")
  const [drillCategory, setDrillCategory] = useState<string | null>(null)

  const range = presetRange(preset)

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "spending", range, drillCategory],
    queryFn: () => reportsApi.spendingByCategory(range.from, range.to, drillCategory ?? undefined),
  })

  const pieData = (data?.categories ?? [])
    .filter((c) => Number(c.amount) !== 0)
    .map((c) => ({ name: c.name, value: Math.abs(Number(c.amount)), id: c.category_id }))

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Spending by Category</h1>
        {drillCategory && (
          <button
            onClick={() => setDrillCategory(null)}
            className="text-sm text-indigo-600 hover:underline"
          >
            ← All categories
          </button>
        )}
      </div>

      <div className="flex gap-1">
        {(
          [
            { label: "This month", key: "this_month" as Preset },
            { label: "3 months", key: "3m" as Preset },
            { label: "6 months", key: "6m" as Preset },
            { label: "12 months", key: "12m" as Preset },
          ] as { label: string; key: Preset }[]
        ).map((p) => (
          <button
            key={p.key}
            onClick={() => {
              setPreset(p.key)
              setDrillCategory(null)
            }}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              preset === p.key
                ? "bg-indigo-600 border-indigo-600 text-white"
                : "border-gray-300 text-gray-600 hover:bg-gray-50"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
      {error && <div className="text-sm text-red-500 py-4">Failed to load report.</div>}

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <p className="text-sm font-semibold text-gray-700 mb-1">Total</p>
            <p className="text-2xl font-semibold text-gray-900 mb-4">
              {formatCurrency(data.total)}
            </p>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Legend iconType="circle" iconSize={8} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-400 py-8 text-center">No spending data.</p>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Breakdown
              </p>
            </div>
            <div className="divide-y divide-gray-100">
              {data.categories.map((c, i) => (
                <div key={c.category_id ?? c.name} className="px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
                    />
                    <span className="flex-1 text-sm text-gray-800 truncate">{c.name}</span>
                    {c.has_children && c.category_id && (
                      <button
                        onClick={() => setDrillCategory(c.category_id)}
                        className="text-xs text-indigo-600 hover:underline shrink-0"
                      >
                        drill down
                      </button>
                    )}
                    <span className="text-sm font-medium text-gray-900">
                      {formatCurrency(c.amount)}
                    </span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.min(100, c.percentage)}%`,
                        backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                      }}
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {c.percentage.toFixed(1)}% · {c.transaction_count} transactions
                  </p>
                </div>
              ))}
              {data.categories.length === 0 && (
                <p className="px-4 py-8 text-center text-gray-400">No data for this period.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
