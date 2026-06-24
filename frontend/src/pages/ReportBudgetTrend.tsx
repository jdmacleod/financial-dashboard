import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts"
import { reportsApi } from "@/api/reports"
import { formatCurrency } from "@/lib/formatters"
import { lastNMonthsRange, lastNYearsRange } from "@/lib/dateRange"

type Preset = "6m" | "1y" | "2y"

const PRESETS: { label: string; key: Preset }[] = [
  { label: "6 Months", key: "6m" },
  { label: "1 Year", key: "1y" },
  { label: "2 Years", key: "2y" },
]

function presetRange(p: Preset) {
  if (p === "6m") return lastNMonthsRange(6)
  if (p === "1y") return lastNMonthsRange(12)
  return lastNYearsRange(2)
}

export default function ReportBudgetTrend() {
  const [preset, setPreset] = useState<Preset>("1y")
  const range = presetRange(preset)

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "budget-trend", range],
    queryFn: () => reportsApi.budgetTrend(range.from, range.to),
  })

  const chartData = data?.series.map((p) => ({
    date: p.period,
    Budget: Number(p.budget),
    Actual: Number(p.actual),
    Variance: Number(p.variance),
  }))

  const overUnder = data ? Number(data.total_variance) : 0

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Budget Trend</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Total budgeted vs actual spend each month. Positive variance means you came in under
          budget.
        </p>
      </div>

      {data && data.series.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Total budgeted</p>
            <p className="text-xl font-semibold text-gray-700">
              {formatCurrency(data.total_budget)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Total actual</p>
            <p className="text-xl font-semibold text-gray-900">
              {formatCurrency(data.total_actual)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">
              {overUnder >= 0 ? "Under budget" : "Over budget"}
            </p>
            <p
              className={`text-xl font-semibold ${
                overUnder >= 0 ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {formatCurrency(String(Math.abs(overUnder)))}
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex gap-1 mb-4">
          {PRESETS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPreset(p.key)}
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

        {chartData && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip formatter={(v) => formatCurrency(v as number)} />
              <Legend iconType="circle" iconSize={8} />
              <Bar dataKey="Budget" fill="#e5e7eb" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Actual" fill="#c7d2fe" radius={[3, 3, 0, 0]} />
              <Line
                type="monotone"
                dataKey="Variance"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}

        {chartData && chartData.length === 0 && (
          <p className="text-sm text-gray-400 py-8 text-center">No budget data for this period.</p>
        )}
      </div>

      {data && data.series.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Month</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Budget</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Actual</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                  Variance
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[...data.series].reverse().map((p) => {
                const v = Number(p.variance)
                return (
                  <tr key={p.period}>
                    <td className="px-4 py-2 text-gray-600">{p.period}</td>
                    <td className="px-4 py-2 text-right text-gray-700">
                      {formatCurrency(p.budget)}
                    </td>
                    <td className="px-4 py-2 text-right text-gray-900">
                      {formatCurrency(p.actual)}
                    </td>
                    <td
                      className={`px-4 py-2 text-right font-medium ${
                        v >= 0 ? "text-emerald-600" : "text-red-600"
                      }`}
                    >
                      {v >= 0 ? "+" : "−"}
                      {formatCurrency(String(Math.abs(v)))}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
