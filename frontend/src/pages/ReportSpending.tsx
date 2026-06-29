import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { useSearch } from "@tanstack/react-router"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts"
import { reportsApi } from "@/api/reports"
import { categoriesApi } from "@/api/categories"
import { formatCurrency } from "@/lib/formatters"
import { currentMonthRange, lastNMonthsRange } from "@/lib/dateRange"

type Preset = "this_month" | "3m" | "6m" | "12m" | "custom"

function presetRange(p: Exclude<Preset, "custom">) {
  if (p === "this_month") return currentMonthRange()
  if (p === "3m") return lastNMonthsRange(3)
  if (p === "6m") return lastNMonthsRange(6)
  return lastNMonthsRange(12)
}

export default function ReportSpending() {
  const search = useSearch({ from: "/app/reports/spending" })
  // A from+to pair in the URL (e.g. a Cash Flow drill-down) opens in Custom mode
  // on that exact range instead of snapping back to a default preset.
  const hasCustomFromUrl = Boolean(search.from && search.to)
  const [preset, setPreset] = useState<Preset>(hasCustomFromUrl ? "custom" : "this_month")
  const [customFrom, setCustomFrom] = useState<string>(search.from ?? currentMonthRange().from)
  const [customTo, setCustomTo] = useState<string>(search.to ?? currentMonthRange().to)
  const [drillCategory, setDrillCategory] = useState<string | null>(search.category ?? null)

  const range = preset === "custom" ? { from: customFrom, to: customTo } : presetRange(preset)
  const customInvalid = preset === "custom" && customFrom > customTo

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "spending", range, drillCategory],
    queryFn: () => reportsApi.spendingByCategory(range.from, range.to, drillCategory ?? undefined),
    enabled: !customInvalid,
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

  const categoryNameMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const c of categories ?? []) {
      map.set(c.id, c.name)
    }
    return map
  }, [categories])

  // When drilled in, the report's `categories` are the children of the parent,
  // so the parent's own name isn't in the response — resolve it from the
  // categories list. Fall back to a neutral label until that query resolves.
  const drillName = drillCategory ? (categoryNameMap.get(drillCategory) ?? "Subcategory") : null

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
          <>
            <span className="text-gray-300" aria-hidden="true">
              ›
            </span>
            <span className="text-2xl font-semibold text-indigo-700">{drillName}</span>
            <button
              onClick={() => setDrillCategory(null)}
              className="text-sm text-indigo-600 hover:underline"
            >
              ← All categories
            </button>
          </>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1">
        {(
          [
            { label: "This month", key: "this_month" as Preset },
            { label: "3 months", key: "3m" as Preset },
            { label: "6 months", key: "6m" as Preset },
            { label: "12 months", key: "12m" as Preset },
            { label: "Custom", key: "custom" as Preset },
          ] as { label: string; key: Preset }[]
        ).map((p) => (
          <button
            key={p.key}
            // Keep any active drill-down when the time window changes; the query
            // is keyed on [range, drillCategory] so it refetches the drilled
            // subcategories for the new window. "← All categories" exits the drill.
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

        {preset === "custom" && (
          <div className="flex items-center gap-1.5 ml-2 text-xs text-gray-600">
            <input
              type="date"
              aria-label="From date"
              value={customFrom}
              max={customTo}
              onChange={(e) => setCustomFrom(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1"
            />
            <span className="text-gray-400">→</span>
            <input
              type="date"
              aria-label="To date"
              value={customTo}
              min={customFrom}
              onChange={(e) => setCustomTo(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1"
            />
          </div>
        )}
      </div>

      {customInvalid && (
        <p className="text-xs text-amber-600">
          The “from” date must be on or before the “to” date.
        </p>
      )}

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
      {error && <div className="text-sm text-red-500 py-4">Failed to load report.</div>}

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
              {drillCategory ? `Total spending: ${drillName}` : "Total spending"}
            </p>
            {pieData.length > 0 ? (
              // The Breakdown panel on the right is the legend (color dot + name +
              // amount + %), so the chart carries no in-SVG <Legend>. That keeps
              // the donut from being squeezed/clipped by a wrapping legend, and
              // the total is overlaid in the donut center where it reads at a glance.
              <div className="relative">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={110}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatCurrency(v as number)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-semibold text-gray-900">
                    {formatCurrency(data.total)}
                  </span>
                  <span className="text-xs text-gray-400">{pieData.length} categories</span>
                </div>
              </div>
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
