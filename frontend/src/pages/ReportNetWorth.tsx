import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import type { NetWorthBreakdown } from "@/api/types"
import {
  AreaChart,
  Area,
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

type Interval = "monthly" | "quarterly" | "annual"
type Preset = "1y" | "2y" | "5y"

const PENSION_PV_DISCOUNT_RATE = 0.04

const ASSET_BUCKETS: { key: keyof NetWorthBreakdown; label: string }[] = [
  { key: "checking_savings", label: "Cash & Savings" },
  { key: "investment", label: "Investments" },
  { key: "retirement", label: "Retirement" },
  { key: "real_estate", label: "Real Estate" },
  { key: "hsa", label: "HSA" },
  { key: "other_assets", label: "Other Assets" },
]

const LIABILITY_BUCKETS: { key: keyof NetWorthBreakdown; label: string }[] = [
  { key: "mortgage", label: "Mortgage" },
  { key: "other_liabilities", label: "Other Liabilities" },
]

const PRESETS: { label: string; key: Preset }[] = [
  { label: "1 Year", key: "1y" },
  { label: "2 Years", key: "2y" },
  { label: "5 Years", key: "5y" },
]

function presetRange(p: Preset) {
  if (p === "1y") return lastNMonthsRange(12)
  if (p === "2y") return lastNYearsRange(2)
  return lastNYearsRange(5)
}

export default function ReportNetWorth() {
  const [preset, setPreset] = useState<Preset>("1y")
  const [interval, setInterval] = useState<Interval>("monthly")
  const [showPV, setShowPV] = useState(false)

  const range = presetRange(preset)

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "net-worth", range, interval],
    queryFn: () => reportsApi.netWorth(range.from, range.to, interval),
  })

  const chartData = data?.series.map((p) => ({
    date: p.date.slice(0, 7),
    Assets: Number(p.total_assets),
    Liabilities: Number(p.total_liabilities),
    "Net Worth": Number(p.net_worth),
  }))

  const current = data?.current

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Net Worth</h1>

      {current && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Net Worth</p>
            <p className="text-xl font-semibold text-indigo-600">
              {formatCurrency(current.net_worth)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Total Assets</p>
            <p className="text-xl font-semibold text-emerald-600">
              {formatCurrency(current.total_assets)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 mb-1">Total Liabilities</p>
            <p className="text-xl font-semibold text-red-600">
              {formatCurrency(current.total_liabilities)}
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex gap-1">
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
          <div className="flex gap-1">
            {(["monthly", "quarterly", "annual"] as Interval[]).map((iv) => (
              <button
                key={iv}
                onClick={() => setInterval(iv)}
                className={`rounded-full px-3 py-1 text-xs font-medium border capitalize transition-colors ${
                  interval === iv
                    ? "bg-indigo-600 border-indigo-600 text-white"
                    : "border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>

        {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
        {error && <div className="text-sm text-red-500 py-4">Failed to load report.</div>}

        {chartData && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
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
              <Area
                type="monotone"
                dataKey="Assets"
                stroke="#10b981"
                fill="#d1fae5"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="Liabilities"
                stroke="#ef4444"
                fill="#fee2e2"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="Net Worth"
                stroke="#6366f1"
                fill="#e0e7ff"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}

        {chartData && chartData.length === 0 && (
          <p className="text-sm text-gray-400 py-8 text-center">No data for this period.</p>
        )}
      </div>

      {data?.series && data.series.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">Period</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">Assets</th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                  Liabilities
                </th>
                <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                  Net Worth
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[...data.series].reverse().map((p) => (
                <tr key={p.date}>
                  <td className="px-4 py-2 text-gray-600">{p.date.slice(0, 7)}</td>
                  <td className="px-4 py-2 text-right text-emerald-600">
                    {formatCurrency(p.total_assets)}
                  </td>
                  <td className="px-4 py-2 text-right text-red-600">
                    {formatCurrency(p.total_liabilities)}
                  </td>
                  <td className="px-4 py-2 text-right font-medium text-gray-900">
                    {formatCurrency(p.net_worth)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data?.current && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Breakdown</h2>
          <div className="grid grid-cols-2 gap-x-8 gap-y-1">
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Assets
              </p>
              <div className="space-y-2.5">
                {ASSET_BUCKETS.map(({ key, label }) => {
                  const amount = Number(data.current!.breakdown[key])
                  const total = Number(data.current!.total_assets)
                  const pct = total > 0 ? (amount / total) * 100 : 0
                  return (
                    <div key={key} className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-1.5 min-w-0">
                        <div
                          className="bg-emerald-500 h-1.5 rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-900 w-20 text-right shrink-0">
                        {formatCurrency(String(amount))}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Liabilities
              </p>
              <div className="space-y-2.5">
                {LIABILITY_BUCKETS.map(({ key, label }) => {
                  const amount = Math.abs(Number(data.current!.breakdown[key]))
                  const total = Number(data.current!.total_liabilities)
                  const pct = total > 0 ? (amount / total) * 100 : 0
                  return (
                    <div key={key} className="flex items-center gap-2">
                      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-1.5 min-w-0">
                        <div
                          className="bg-red-400 h-1.5 rounded-full"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-900 w-20 text-right shrink-0">
                        {formatCurrency(String(amount))}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {data?.pension_annotations && data.pension_annotations.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">Pension Accounts</h2>
            <button
              onClick={() => setShowPV(!showPV)}
              className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                showPV
                  ? "bg-indigo-600 border-indigo-600 text-white"
                  : "border-gray-300 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {showPV ? "Showing PV" : "Show PV"}
            </button>
          </div>
          <div className="space-y-3">
            {data.pension_annotations.map((ann) => {
              const annualBenefit =
                ann.monthly_benefit != null ? Number(ann.monthly_benefit) * 12 : null
              const presentValue =
                annualBenefit != null ? annualBenefit / PENSION_PV_DISCOUNT_RATE : null
              return (
                <div
                  key={ann.account_id}
                  className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
                >
                  <div>
                    <Link
                      to="/accounts/$accountId/pension"
                      params={{ accountId: ann.account_id }}
                      className="font-medium text-sm text-indigo-600 hover:underline"
                    >
                      {ann.nickname}
                    </Link>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {ann.eligibility_age != null && `Eligible at ${ann.eligibility_age}`}
                      {ann.eligibility_age != null && ann.eligibility_date && " · "}
                      {ann.eligibility_date && ann.eligibility_date}
                    </p>
                  </div>
                  <div className="text-right">
                    {ann.monthly_benefit != null ? (
                      <>
                        <p className="text-sm font-medium text-gray-900">
                          {showPV && presentValue != null
                            ? `${formatCurrency(String(presentValue))} PV`
                            : `${formatCurrency(String(annualBenefit))} / yr`}
                        </p>
                        <p className="text-xs text-gray-400">
                          {formatCurrency(ann.monthly_benefit)} / mo
                        </p>
                      </>
                    ) : (
                      <p className="text-sm text-gray-400">No estimate</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
          {showPV && (
            <p className="mt-3 text-xs text-gray-400">
              Present value estimated using {PENSION_PV_DISCOUNT_RATE * 100}% discount rate (annual
              benefit ÷ {PENSION_PV_DISCOUNT_RATE}).
            </p>
          )}
        </div>
      )}
    </div>
  )
}
