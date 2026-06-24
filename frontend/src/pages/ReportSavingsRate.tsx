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

export default function ReportSavingsRate() {
  const [preset, setPreset] = useState<Preset>("1y")
  const range = presetRange(preset)

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "savings-rate", range],
    queryFn: () => reportsApi.savingsRate(range.from, range.to),
  })

  const chartData = data?.series.map((p) => ({
    date: p.period,
    Savings: Number(p.savings),
    "Savings rate": Number(p.savings_rate.toFixed(1)),
    "3-mo avg": Number(p.rolling_rate.toFixed(1)),
  }))

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Savings Rate</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          The share of income you keep each month — the single biggest lever on time to financial
          independence.
        </p>
      </div>

      {data && data.series.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Average rate</p>
            <p className="text-xl font-semibold text-indigo-600">{data.average_rate.toFixed(1)}%</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Best month</p>
            <p className="text-xl font-semibold text-emerald-600">{data.best_period ?? "—"}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Leanest month</p>
            <p className="text-xl font-semibold text-gray-700">{data.worst_period ?? "—"}</p>
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
                yAxisId="left"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip
                formatter={(v, name) =>
                  name === "Savings" ? formatCurrency(v as number) : `${v}%`
                }
              />
              <Legend iconType="circle" iconSize={8} />
              <Bar yAxisId="left" dataKey="Savings" fill="#c7d2fe" radius={[3, 3, 0, 0]} />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="Savings rate"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="3-mo avg"
                stroke="#10b981"
                strokeWidth={2}
                strokeDasharray="4 3"
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}

        {chartData && chartData.length === 0 && (
          <p className="text-sm text-gray-400 py-8 text-center">No income data for this period.</p>
        )}
      </div>

      {data && data.series.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Month</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Income</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                  Expenses
                </th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Saved</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[...data.series].reverse().map((p) => (
                <tr key={p.period}>
                  <td className="px-4 py-2 text-gray-600">{p.period}</td>
                  <td className="px-4 py-2 text-right text-emerald-600">
                    {formatCurrency(p.income)}
                  </td>
                  <td className="px-4 py-2 text-right text-red-600">
                    {formatCurrency(p.expenses)}
                  </td>
                  <td className="px-4 py-2 text-right font-medium text-gray-900">
                    {formatCurrency(p.savings)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-medium ${
                      p.savings_rate >= 0 ? "text-indigo-600" : "text-red-600"
                    }`}
                  >
                    {p.savings_rate.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
