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
import { lastNMonthsRange } from "@/lib/dateRange"

type GroupBy = "month" | "quarter"

export default function ReportCashFlow() {
  const [months, setMonths] = useState(12)
  const [groupBy, setGroupBy] = useState<GroupBy>("month")

  const range = lastNMonthsRange(months)

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "cash-flow", range, groupBy],
    queryFn: () => reportsApi.cashFlow(range.from, range.to, groupBy),
  })

  const chartData = data?.series.map((p) => ({
    period: p.period,
    Income: Number(p.income),
    Expenses: Math.abs(Number(p.expenses)),
    Net: Number(p.net),
  }))

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Cash Flow</h1>

      {data?.totals && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Total Income</p>
            <p className="text-xl font-semibold text-emerald-600">
              {formatCurrency(data.totals.income)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Total Expenses</p>
            <p className="text-xl font-semibold text-red-600">
              {formatCurrency(data.totals.expenses)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Savings Rate</p>
            <p
              className={`text-xl font-semibold ${data.totals.savings_rate >= 0 ? "text-indigo-600" : "text-red-600"}`}
            >
              {data.totals.savings_rate.toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex gap-1">
            {[6, 12, 24].map((m) => (
              <button
                key={m}
                onClick={() => setMonths(m)}
                className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                  months === m
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {m}m
              </button>
            ))}
          </div>
          <div className="flex gap-1">
            {(["month", "quarter"] as GroupBy[]).map((g) => (
              <button
                key={g}
                onClick={() => setGroupBy(g)}
                className={`rounded-full px-3 py-1 text-xs font-medium border capitalize transition-colors ${
                  groupBy === g
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>

        {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
        {error && <div className="text-sm text-red-500 py-4">Failed to load report.</div>}

        {chartData && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip formatter={(v: number) => formatCurrency(v)} />
              <Legend iconType="circle" iconSize={8} />
              <Bar dataKey="Income" fill="#10b981" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Expenses" fill="#ef4444" radius={[3, 3, 0, 0]} />
              <Line type="monotone" dataKey="Net" stroke="#6366f1" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>

      {data?.series && data.series.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Period</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Income</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                  Expenses
                </th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Net</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                  Savings %
                </th>
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
                  <td
                    className={`px-4 py-2 text-right font-medium ${Number(p.net) >= 0 ? "text-indigo-600" : "text-red-600"}`}
                  >
                    {formatCurrency(p.net)}
                  </td>
                  <td className="px-4 py-2 text-right text-gray-600">
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
