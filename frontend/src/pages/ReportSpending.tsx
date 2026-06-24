import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { useSearch } from "@tanstack/react-router"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { reportsApi } from "@/api/reports"
import { categoriesApi } from "@/api/categories"
import { formatCurrency } from "@/lib/formatters"
import { currentMonthRange, lastNMonthsRange } from "@/lib/dateRange"

type Preset = "this_month" | "3m" | "6m" | "12m"

function presetRange(p: Preset) {
  if (p === "this_month") return currentMonthRange()
  if (p === "3m") return lastNMonthsRange(3)
  if (p === "6m") return lastNMonthsRange(6)
  return lastNMonthsRange(12)
}

export default function ReportSpending() {
  const search = useSearch({ from: "/app/reports/spending" })
  const [preset, setPreset] = useState<Preset>("this_month")
  const [drillCategory, setDrillCategory] = useState<string | null>(search.category ?? null)

  const range = presetRange(preset)

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "spending", range, drillCategory],
    queryFn: () => reportsApi.spendingByCategory(range.from, range.to, drillCategory ?? undefined),
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
    staleTime: 5 * 60 * 1000,
  })

  const categoryColorMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const c of categories ?? []) {
      map.set(c.id, c.color_hex)
    }
    return map
  }, [categories])

  const pieData = (data?.categories ?? [])
    .filter((c) => Number(c.amount) !== 0)
    .map((c) => ({
      name: c.name,
      value: Math.abs(Number(c.amount)),
      id: c.category_id,
      color: c.category_id ? (categoryColorMap.get(c.category_id) ?? "#888888") : "#888888",
    }))

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
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => formatCurrency(v as number)} />
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
              {data.categories.map((c) => {
                const entryColor = c.category_id
                  ? (categoryColorMap.get(c.category_id) ?? "#888888")
                  : "#888888"
                return (
                  <div key={c.category_id ?? c.name} className="px-4 py-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="h-2 w-2 rounded-full shrink-0"
                        style={{ backgroundColor: entryColor }}
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
                          backgroundColor: entryColor,
                        }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {c.percentage.toFixed(1)}% · {c.transaction_count} transactions
                    </p>
                  </div>
                )
              })}
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
