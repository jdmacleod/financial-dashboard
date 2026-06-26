import { useState, useMemo, useEffect } from "react"
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { format, subMonths, addMonths, startOfYear } from "date-fns"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { budgetsApi } from "@/api/budgets"
import { reportsApi } from "@/api/reports"
import { categoriesApi } from "@/api/categories"
import { formatCurrency } from "@/lib/formatters"
import { loadSort, persistSort } from "@/lib/sortStorage"
import type { BudgetPeriod, BudgetResponse, BudgetVsActualsItem } from "@/api/types"

// ── Types ────────────────────────────────────────────────────────────────────

type RangeMode = "month" | "ytd" | "1y" | "all"
type ActualsSort = "pct_used_desc" | "budget_desc" | "actual_desc" | "name_asc"
type BudgetsSort = "name_asc" | "budget_desc" | "period"

// ── Sort preference persistence ──────────────────────────────────────────────
// Persist the chosen sort keys to localStorage so power users don't re-apply
// them every visit. Stored values are validated against the allowed set on read,
// so a renamed/removed sort option falls back to the default rather than sticking.

const ACTUALS_SORTS: readonly ActualsSort[] = [
  "pct_used_desc",
  "budget_desc",
  "actual_desc",
  "name_asc",
]
const BUDGETS_SORTS: readonly BudgetsSort[] = ["name_asc", "budget_desc", "period"]
const ACTUALS_SORT_KEY = "hl.budgets.actualsSort"
const BUDGETS_SORT_KEY = "hl.budgets.budgetsSort"

// ── Utilities ────────────────────────────────────────────────────────────────

function currentMonth() {
  return format(new Date(), "yyyy-MM")
}

function localMonthDate(monthStr: string): Date {
  const [y, m] = monthStr.split("-").map(Number)
  return new Date(y, m - 1, 1)
}

function monthsBetween(from: string, to: string): string[] {
  const months: string[] = []
  let d = localMonthDate(from)
  const end = localMonthDate(to)
  while (d <= end) {
    months.push(format(d, "yyyy-MM"))
    d = addMonths(d, 1)
  }
  return months
}

function rangeMonths(
  mode: RangeMode,
  currentMonthStr: string,
  earliestBudgetMonth: string,
): string[] {
  const curDate = localMonthDate(currentMonthStr)
  if (mode === "month") return [currentMonthStr]
  if (mode === "ytd") {
    const jan = format(startOfYear(curDate), "yyyy-MM")
    return monthsBetween(jan, currentMonthStr)
  }
  if (mode === "1y") {
    const from = format(subMonths(curDate, 11), "yyyy-MM")
    return monthsBetween(from, currentMonthStr)
  }
  // "all" — from earliest budget start, capped at 48 months
  const cap = format(subMonths(curDate, 47), "yyyy-MM")
  const from = earliestBudgetMonth > cap ? earliestBudgetMonth : cap
  return monthsBetween(from, currentMonthStr)
}

function aggregateItems(reports: { categories: BudgetVsActualsItem[] }[]): BudgetVsActualsItem[] {
  const agg = new Map<
    string,
    { name: string; budget: number; actual: number; period: BudgetPeriod }
  >()
  for (const rpt of reports) {
    for (const item of rpt.categories) {
      const existing = agg.get(item.category_id)
      if (existing) {
        existing.budget += Number(item.budget)
        existing.actual += Number(item.actual)
      } else {
        agg.set(item.category_id, {
          name: item.name,
          budget: Number(item.budget),
          actual: Number(item.actual),
          period: item.period ?? "monthly",
        })
      }
    }
  }
  return Array.from(agg.entries()).map(([id, v]) => ({
    category_id: id,
    name: v.name,
    budget: v.budget.toFixed(2),
    actual: v.actual.toFixed(2),
    remaining: (v.budget - v.actual).toFixed(2),
    percentage_used: v.budget > 0 ? (v.actual / v.budget) * 100 : 0,
    period: v.period,
  }))
}

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

// ── Period helpers ───────────────────────────────────────────────────────────

const PERIOD_DIVISOR: Record<BudgetPeriod, number> = { monthly: 1, quarterly: 3, annual: 12 }

function periodAmountLabel(period: BudgetPeriod): string {
  if (period === "annual") return "Annual amount"
  if (period === "quarterly") return "Quarterly amount"
  return "Monthly amount"
}

function prorationNote(period: BudgetPeriod): string | null {
  const divisor = PERIOD_DIVISOR[period]
  return divisor > 1 ? `Shown as ÷${divisor} per month in budget vs actuals.` : null
}

function periodSuffix(period: BudgetPeriod): string {
  if (period === "annual") return "/yr"
  if (period === "quarterly") return "/qtr"
  return "/mo"
}

// ── Schemas ──────────────────────────────────────────────────────────────────

const createSchema = z.object({
  category_id: z.string().min(1, "Required"),
  period: z.enum(["monthly", "quarterly", "annual"]),
  amount: z
    .string()
    .min(1, "Required")
    .refine((v) => Number(v) > 0, "Amount must be greater than 0"),
  effective_from: z.string().min(1, "Required"),
})
type CreateForm = z.infer<typeof createSchema>

const editSchema = z.object({
  period: z.enum(["monthly", "quarterly", "annual"]),
  amount: z
    .string()
    .min(1, "Required")
    .refine((v) => Number(v) > 0, "Amount must be greater than 0"),
  effective_from: z.string().min(1, "Required"),
  effective_to: z.string().optional(),
})
type EditForm = z.infer<typeof editSchema>

// ── AddBudgetModal ───────────────────────────────────────────────────────────

function AddBudgetModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list })

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { period: "monthly", effective_from: format(new Date(), "yyyy-MM-dd") },
  })

  const period = watch("period")

  const create = useMutation({
    mutationFn: (data: CreateForm) =>
      budgetsApi.create({
        category_id: data.category_id,
        period: data.period,
        amount: data.amount,
        effective_from: data.effective_from,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] })
      queryClient.invalidateQueries({ queryKey: ["reports", "budget-vs-actuals"] })
      onClose()
    },
    onError: () => setError("Failed to create budget."),
  })

  const expenseCategories = categories?.filter((c) => !c.is_income) ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Add Budget</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select
              {...register("category_id")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select a category…</option>
              {expenseCategories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            {errors.category_id && (
              <p className="mt-1 text-xs text-red-600">{errors.category_id.message}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Period</label>
            <div className="flex gap-2">
              {(["monthly", "quarterly", "annual"] as const).map((p) => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    {...register("period")}
                    value={p}
                    className="accent-indigo-600"
                  />
                  <span className="text-sm capitalize">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {periodAmountLabel(period)}
            </label>
            <input
              {...register("amount")}
              placeholder={period === "annual" ? "e.g. 3800.00" : "e.g. 500.00"}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {prorationNote(period) && (
              <p className="mt-1 text-xs text-gray-400">{prorationNote(period)}</p>
            )}
            {errors.amount && <p className="mt-1 text-xs text-red-600">{errors.amount.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Effective from</label>
            <input
              type="date"
              {...register("effective_from")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {isSubmitting ? "Adding…" : "Add Budget"}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── EditBudgetModal ──────────────────────────────────────────────────────────

function EditBudgetModal({
  budget,
  categoryName,
  onClose,
}: {
  budget: BudgetResponse
  categoryName: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<EditForm>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      period: budget.period as BudgetPeriod,
      amount: budget.amount,
      effective_from: budget.effective_from,
      effective_to: budget.effective_to ?? "",
    },
  })

  const period = watch("period")

  const update = useMutation({
    mutationFn: (data: EditForm) =>
      budgetsApi.update(budget.id, {
        amount: data.amount,
        effective_from: data.effective_from,
        effective_to: data.effective_to || null,
        period: data.period,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] })
      queryClient.invalidateQueries({ queryKey: ["reports", "budget-vs-actuals"] })
      onClose()
    },
    onError: () => setError("Failed to update budget."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-semibold">Edit Budget</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{categoryName}</p>
        <form onSubmit={handleSubmit((d) => update.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Period</label>
            <div className="flex gap-2">
              {(["monthly", "quarterly", "annual"] as const).map((p) => (
                <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="radio"
                    {...register("period")}
                    value={p}
                    className="accent-indigo-600"
                  />
                  <span className="text-sm capitalize">{p}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {periodAmountLabel(period)}
            </label>
            <input
              {...register("amount")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {prorationNote(period) && (
              <p className="mt-1 text-xs text-gray-400">{prorationNote(period)}</p>
            )}
            {errors.amount && <p className="mt-1 text-xs text-red-600">{errors.amount.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Effective from</label>
            <input
              type="date"
              {...register("effective_from")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Effective to{" "}
              <span className="text-gray-400 font-normal">
                (optional — leave blank for ongoing)
              </span>
            </label>
            <input
              type="date"
              {...register("effective_to")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {isSubmitting ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── BudgetRow ────────────────────────────────────────────────────────────────

function BudgetRow({
  budget,
  categoryName,
  onDelete,
}: {
  budget: BudgetResponse
  categoryName: string
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const periodLabel = periodSuffix(budget.period)

  return (
    <>
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900">
            {formatCurrency(budget.amount)}
            <span className="text-gray-400 font-normal">{periodLabel}</span>
            {budget.period !== "monthly" && (
              <span className="ml-1.5 text-xs text-gray-400">
                (≈
                {formatCurrency(
                  String((Number(budget.amount) / PERIOD_DIVISOR[budget.period]).toFixed(2)),
                )}
                /mo)
              </span>
            )}
          </p>
          <p className="text-xs text-gray-400">
            from {budget.effective_from}
            {budget.effective_to ? ` · to ${budget.effective_to}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Edit
          </button>
          <button onClick={onDelete} className="text-xs text-red-500 hover:text-red-700">
            Delete
          </button>
        </div>
      </div>
      {editing && (
        <EditBudgetModal
          budget={budget}
          categoryName={categoryName}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  )
}

// ── BudgetDonutChart ─────────────────────────────────────────────────────────

function BudgetDonutChart({ items }: { items: BudgetVsActualsItem[] }) {
  const TOP_N = 9
  const sorted = [...items].sort((a, b) => Number(b.budget) - Number(a.budget))
  const top = sorted.slice(0, TOP_N)
  const rest = sorted.slice(TOP_N)
  const otherBudget = rest.reduce((s, i) => s + Number(i.budget), 0)

  const data = [
    ...top.map((i) => ({ name: i.name, value: Number(i.budget) })),
    ...(otherBudget > 0 ? [{ name: "Other", value: otherBudget }] : []),
  ]

  const totalBudget = items.reduce((s, i) => s + Number(i.budget), 0)
  const totalActual = items.reduce((s, i) => s + Number(i.actual), 0)
  const overallPct = totalBudget > 0 ? (totalActual / totalBudget) * 100 : 0

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-start gap-4">
        <div className="w-48 h-48 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={72}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => formatCurrency(String(Number(v).toFixed(2)))} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex-1 min-w-0">
          <div className="mb-3">
            <p className="text-xs text-gray-500 uppercase tracking-wide font-semibold">
              Total budgeted
            </p>
            <p className="text-2xl font-semibold text-gray-900">
              {formatCurrency(String(totalBudget.toFixed(2)))}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">
              {formatCurrency(String(totalActual.toFixed(2)))} spent · {overallPct.toFixed(0)}% used
            </p>
          </div>
          <div className="space-y-1.5">
            {data.slice(0, TOP_N).map((d, i) => (
              <div key={d.name} className="flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                  style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                />
                <span className="text-xs text-gray-600 truncate flex-1">{d.name}</span>
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {formatCurrency(String(d.value.toFixed(2)))}
                </span>
              </div>
            ))}
            {data.length > TOP_N && (
              <p className="text-xs text-gray-400">+ {data.length - TOP_N} more</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── RangeToggle ──────────────────────────────────────────────────────────────

function RangeToggle({ mode, onChange }: { mode: RangeMode; onChange: (m: RangeMode) => void }) {
  const modes: { key: RangeMode; label: string }[] = [
    { key: "month", label: "Month" },
    { key: "ytd", label: "YTD" },
    { key: "1y", label: "1Y" },
    { key: "all", label: "All" },
  ]
  return (
    <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
      {modes.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
            mode === key
              ? "bg-white text-gray-900 shadow-sm border border-gray-200"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

// ── RangeLabel ───────────────────────────────────────────────────────────────

function rangeSummaryLabel(mode: RangeMode, months: string[]): string {
  if (mode === "month" || months.length === 0) return ""
  const first = months[0]
  const last = months[months.length - 1]
  const fmt = (m: string) => {
    const [y, mo] = m.split("-").map(Number)
    return format(new Date(y, mo - 1, 1), "MMM yyyy")
  }
  return `${fmt(first)} – ${fmt(last)}`
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function Budgets() {
  const queryClient = useQueryClient()
  const [month, setMonth] = useState(currentMonth())
  const [rangeMode, setRangeMode] = useState<RangeMode>("month")
  const [showAdd, setShowAdd] = useState(false)
  const [filterText, setFilterText] = useState("")
  const [actualsSort, setActualsSort] = useState<ActualsSort>(() =>
    loadSort(ACTUALS_SORT_KEY, ACTUALS_SORTS, "pct_used_desc"),
  )
  const [budgetsSort, setBudgetsSort] = useState<BudgetsSort>(() =>
    loadSort(BUDGETS_SORT_KEY, BUDGETS_SORTS, "name_asc"),
  )

  useEffect(() => persistSort(ACTUALS_SORT_KEY, actualsSort), [actualsSort])
  useEffect(() => persistSort(BUDGETS_SORT_KEY, budgetsSort), [budgetsSort])

  const { data: budgets } = useQuery({
    queryKey: ["budgets"],
    queryFn: () => budgetsApi.list(),
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  })

  // Determine months to fetch based on range mode
  const earliestBudgetMonth = useMemo(() => {
    if (!budgets?.length) return format(subMonths(new Date(), 35), "yyyy-MM")
    const earliest = budgets.reduce(
      (min, b) => (b.effective_from < min ? b.effective_from : min),
      "9999-12-31", // sentinel: any real date compares as less
    )
    return earliest.substring(0, 7)
  }, [budgets])

  const monthsToFetch = useMemo(
    () => rangeMonths(rangeMode, month, earliestBudgetMonth),
    [rangeMode, month, earliestBudgetMonth],
  )

  // Fetch all required months in parallel
  const monthQueries = useQueries({
    queries: monthsToFetch.map((m) => ({
      queryKey: ["reports", "budget-vs-actuals", m],
      queryFn: () => reportsApi.budgetVsActuals(m),
    })),
  })

  const reportLoading = monthQueries.some((q) => q.isLoading)
  const reportError =
    !reportLoading && monthQueries.length > 0 && monthQueries.every((q) => q.isError)
  const reportPartialError = !reportLoading && !reportError && monthQueries.some((q) => q.isError)
  const reportItems = useMemo(() => {
    const completed = monthQueries.filter((q) => q.data).map((q) => q.data!)
    if (completed.length === 0) return []
    return aggregateItems(completed)
  }, [monthQueries])

  const removeBudget = useMutation({
    mutationFn: (id: string) => budgetsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] })
      queryClient.invalidateQueries({ queryKey: ["reports", "budget-vs-actuals"] })
    },
  })

  function prevMonth() {
    const [y, m] = month.split("-").map(Number)
    setMonth(format(subMonths(new Date(y, m - 1, 1), 1), "yyyy-MM"))
  }
  function nextMonth() {
    const [y, m] = month.split("-").map(Number)
    setMonth(format(addMonths(new Date(y, m - 1, 1), 1), "yyyy-MM"))
  }

  const categoryMap = useMemo(() => new Map(categories?.map((c) => [c.id, c]) ?? []), [categories])

  const rangeLabel = rangeMode !== "month" ? rangeSummaryLabel(rangeMode, monthsToFetch) : month

  const loadedCount = monthQueries.filter((q) => q.data).length
  const loadingProgress =
    reportLoading && monthsToFetch.length > 1
      ? `${loadedCount} / ${monthsToFetch.length} months`
      : null

  const filteredReportItems = useMemo(() => {
    if (!filterText) return reportItems
    const lower = filterText.toLowerCase()
    return reportItems.filter((i) => i.name.toLowerCase().includes(lower))
  }, [reportItems, filterText])

  const sortedReportItems = useMemo(() => {
    return [...filteredReportItems].sort((a, b) => {
      if (actualsSort === "pct_used_desc") return b.percentage_used - a.percentage_used
      if (actualsSort === "budget_desc") return Number(b.budget) - Number(a.budget)
      if (actualsSort === "actual_desc") return Number(b.actual) - Number(a.actual)
      return a.name.localeCompare(b.name)
    })
  }, [filteredReportItems, actualsSort])

  const filteredBudgets = useMemo(() => {
    if (!budgets) return []
    if (!filterText) return budgets
    const lower = filterText.toLowerCase()
    return budgets.filter((b) => {
      const name = categoryMap.get(b.category_id)?.name ?? ""
      return name.toLowerCase().includes(lower)
    })
  }, [budgets, categoryMap, filterText])

  const sortedBudgets = useMemo(() => {
    return [...filteredBudgets].sort((a, b) => {
      const nameA = categoryMap.get(a.category_id)?.name ?? ""
      const nameB = categoryMap.get(b.category_id)?.name ?? ""
      if (budgetsSort === "name_asc") return nameA.localeCompare(nameB)
      if (budgetsSort === "budget_desc") return Number(b.amount) - Number(a.amount)
      if (budgetsSort === "period") {
        // Order by cadence: monthly → quarterly → annual (PERIOD_DIVISOR is 1/3/12).
        if (a.period === b.period) return nameA.localeCompare(nameB)
        return PERIOD_DIVISOR[a.period] - PERIOD_DIVISOR[b.period]
      }
      return 0
    })
  }, [filteredBudgets, budgetsSort, categoryMap])

  const visibleCount = filteredReportItems.length
  const totalCount = reportItems.length

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Budgets</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Add budget
        </button>
      </div>

      {/* Range mode toggle + month navigator */}
      <div className="flex items-center gap-3 flex-wrap">
        <RangeToggle mode={rangeMode} onChange={setRangeMode} />
        {rangeMode === "month" ? (
          <div className="flex items-center gap-2">
            <button
              onClick={prevMonth}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              aria-label="Previous month"
            >
              ←
            </button>
            <span className="text-sm font-medium text-gray-800 w-24 text-center">{month}</span>
            <button
              onClick={nextMonth}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              aria-label="Next month"
            >
              →
            </button>
          </div>
        ) : (
          <span className="text-sm text-gray-500">{rangeLabel}</span>
        )}
        {loadingProgress && (
          <span className="text-xs text-gray-400 ml-auto">Loading {loadingProgress}…</span>
        )}
      </div>

      {/* Donut chart overview — only show when we have data */}
      {reportItems.length > 0 && <BudgetDonutChart items={reportItems} />}

      {/* Filter bar — below donut so donut's independence from the filter is visually clear */}
      {(reportItems.length > 0 || (budgets && budgets.length > 0)) && (
        <div className="flex items-center gap-3">
          <div role="search" className="relative flex-1 max-w-xs">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.5" />
                <line
                  x1="9.5"
                  y1="9.5"
                  x2="13"
                  y2="13"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <input
              aria-label="Filter categories"
              placeholder="Filter categories…"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {filterText && (
            <span
              aria-live="polite"
              className="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5 flex-shrink-0"
            >
              {visibleCount} of {totalCount}
            </span>
          )}
          {filterText && (
            <button
              onClick={() => setFilterText("")}
              className="text-xs text-indigo-600 hover:text-indigo-800 flex-shrink-0 py-1 px-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              Clear
            </button>
          )}
        </div>
      )}

      {/* Budget vs Actuals report */}
      {reportLoading && loadedCount === 0 && <div className="text-sm text-gray-400">Loading…</div>}
      {reportError && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Could not load budget data. Please try again.
        </div>
      )}
      {reportPartialError && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Some months could not be loaded — totals shown may be incomplete.
        </div>
      )}

      {reportItems.length > 0 && (
        <div
          data-testid="section-actuals"
          className="bg-white rounded-xl border border-gray-200 overflow-hidden"
        >
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Budget vs Actuals — {rangeLabel}
            </p>
            <select
              aria-label="Sort budget vs actuals"
              value={actualsSort}
              onChange={(e) => setActualsSort(e.target.value as ActualsSort)}
              className="text-xs text-gray-500 border-0 bg-transparent cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
            >
              <option value="pct_used_desc">% Used ↓</option>
              <option value="budget_desc">Budget ↓</option>
              <option value="actual_desc">Actual Spend ↓</option>
              <option value="name_asc">Name A-Z</option>
            </select>
          </div>
          {sortedReportItems.length === 0 && filterText ? (
            <div className="px-4 py-6 text-center">
              <p className="text-sm text-gray-400">
                No categories match{" "}
                <span className="font-medium text-gray-600">'{filterText}'</span>.{" "}
                <button
                  onClick={() => setFilterText("")}
                  className="text-indigo-600 hover:text-indigo-800 underline"
                >
                  Clear filter
                </button>
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {sortedReportItems.map((item) => {
                const pct = item.percentage_used
                const isOver = pct > 100
                const barColor = isOver
                  ? "bg-red-500"
                  : pct >= 90
                    ? "bg-amber-500"
                    : "bg-emerald-500"
                return (
                  <div key={item.category_id} className="px-4 py-3">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-sm font-medium text-gray-900 truncate">
                          {item.name}
                        </span>
                        {item.period !== "monthly" && rangeMode === "month" && (
                          <span className="text-xs text-gray-400 flex-shrink-0">
                            {item.period}÷{PERIOD_DIVISOR[item.period]}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                        {formatCurrency(item.actual)} / {formatCurrency(item.budget)}
                      </span>
                    </div>
                    <div className="relative h-2" style={{ marginRight: isOver ? "10px" : "0" }}>
                      <div className="absolute inset-0 bg-gray-100 rounded-full" />
                      <div
                        className={`absolute left-0 top-0 h-full transition-all ${isOver ? "rounded-l-full" : "rounded-full"} ${barColor}`}
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                      {isOver && (
                        <div
                          className="absolute bg-red-700 rounded-r-full"
                          style={{ right: "-10px", top: "-1px", width: "7px", height: "10px" }}
                        />
                      )}
                    </div>
                    <p
                      className={`text-xs mt-0.5 ${isOver ? "font-medium text-red-600" : "text-gray-400"}`}
                    >
                      {pct.toFixed(0)}% used ·{" "}
                      {Number(item.remaining) >= 0
                        ? `${formatCurrency(item.remaining)} remaining`
                        : `${formatCurrency(Math.abs(Number(item.remaining)))} over`}
                    </p>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* All Budgets list (budget definitions) */}
      {budgets && budgets.length > 0 && (
        <div
          data-testid="section-budgets"
          className="bg-white rounded-xl border border-gray-200 overflow-hidden"
        >
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              All Budgets
            </p>
            <select
              aria-label="Sort all budgets"
              value={budgetsSort}
              onChange={(e) => setBudgetsSort(e.target.value as BudgetsSort)}
              className="text-xs text-gray-500 border-0 bg-transparent cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
            >
              <option value="name_asc">Name A-Z</option>
              <option value="budget_desc">Budget ↓</option>
              <option value="period">Period</option>
            </select>
          </div>
          {sortedBudgets.length === 0 && filterText ? (
            <div className="px-4 py-6 text-center">
              <p className="text-sm text-gray-400">
                No categories match{" "}
                <span className="font-medium text-gray-600">'{filterText}'</span>.{" "}
                <button
                  onClick={() => setFilterText("")}
                  className="text-indigo-600 hover:text-indigo-800 underline"
                >
                  Clear filter
                </button>
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {sortedBudgets.map((b) => {
                const cat = categoryMap.get(b.category_id)
                const name = cat?.name ?? b.category_id
                return (
                  <div key={b.id}>
                    <div className="px-4 pt-2 pb-0">
                      <p className="text-xs font-semibold text-gray-600">{name}</p>
                    </div>
                    <BudgetRow
                      budget={b}
                      categoryName={name}
                      onDelete={() => {
                        if (window.confirm("Delete this budget?")) removeBudget.mutate(b.id)
                      }}
                    />
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {budgets?.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">No budgets yet</p>
          <p className="text-sm">Add a budget to start tracking spending goals.</p>
        </div>
      )}

      {showAdd && <AddBudgetModal onClose={() => setShowAdd(false)} />}
    </div>
  )
}
