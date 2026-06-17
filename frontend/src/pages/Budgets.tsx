import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { format, subMonths, addMonths } from "date-fns"
import { budgetsApi } from "@/api/budgets"
import { reportsApi } from "@/api/reports"
import { categoriesApi } from "@/api/categories"
import { formatCurrency } from "@/lib/formatters"
import type { BudgetResponse } from "@/api/types"

function currentMonth() {
  return format(new Date(), "yyyy-MM")
}

const createSchema = z.object({
  category_id: z.string().min(1, "Required"),
  amount: z.string().min(1, "Required"),
  effective_from: z.string().min(1, "Required"),
})
type CreateForm = z.infer<typeof createSchema>

function AddBudgetModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { effective_from: format(new Date(), "yyyy-MM-dd") },
  })

  const create = useMutation({
    mutationFn: (data: CreateForm) =>
      budgetsApi.create({
        category_id: data.category_id,
        period: "monthly",
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
            <label className="block text-sm font-medium text-gray-700 mb-1">Monthly amount</label>
            <input
              {...register("amount")}
              placeholder="e.g. 500.00"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
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

function BudgetRow({ budget, onDelete }: { budget: BudgetResponse; onDelete: () => void }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [amount, setAmount] = useState(budget.amount)

  const update = useMutation({
    mutationFn: (amt: string) => budgetsApi.update(budget.id, { amount: amt }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] })
      queryClient.invalidateQueries({ queryKey: ["reports", "budget-vs-actuals"] })
      setEditing(false)
    },
  })

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="flex-1 min-w-0">
        {editing ? (
          <div className="flex items-center gap-2">
            <input
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-32 rounded-lg border border-gray-300 px-2 py-1 text-sm"
            />
            <button
              onClick={() => update.mutate(amount)}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
            >
              Save
            </button>
            <button
              onClick={() => {
                setAmount(budget.amount)
                setEditing(false)
              }}
              className="text-sm text-gray-500"
            >
              Cancel
            </button>
          </div>
        ) : (
          <p className="text-sm font-medium text-gray-900">{formatCurrency(budget.amount)}/mo</p>
        )}
        <p className="text-xs text-gray-400">from {budget.effective_from}</p>
      </div>
      {!editing && (
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
      )}
    </div>
  )
}

export default function Budgets() {
  const queryClient = useQueryClient()
  const [month, setMonth] = useState(currentMonth())
  const [showAdd, setShowAdd] = useState(false)

  const { data: budgets } = useQuery({
    queryKey: ["budgets"],
    queryFn: () => budgetsApi.list(),
  })

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ["reports", "budget-vs-actuals", month],
    queryFn: () => reportsApi.budgetVsActuals(month),
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  })

  const removeBudget = useMutation({
    mutationFn: (id: string) => budgetsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] })
      queryClient.invalidateQueries({ queryKey: ["reports", "budget-vs-actuals"] })
    },
  })

  function prevMonth() {
    const d = new Date(`${month}-01`)
    setMonth(format(subMonths(d, 1), "yyyy-MM"))
  }
  function nextMonth() {
    const d = new Date(`${month}-01`)
    setMonth(format(addMonths(d, 1), "yyyy-MM"))
  }

  const categoryMap = new Map(categories?.map((c) => [c.id, c]) ?? [])

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

      <div className="flex items-center gap-3">
        <button
          onClick={prevMonth}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          ←
        </button>
        <span className="text-sm font-medium text-gray-800 w-24 text-center">{month}</span>
        <button
          onClick={nextMonth}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          →
        </button>
      </div>

      {reportLoading && <div className="text-sm text-gray-400">Loading…</div>}

      {report && report.categories.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Budget vs Actuals — {report.period}
            </p>
          </div>
          <div className="divide-y divide-gray-100">
            {report.categories.map((item) => (
              <div key={item.category_id} className="px-4 py-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-900">{item.name}</span>
                  <span className="text-xs text-gray-500">
                    {formatCurrency(item.actual)} / {formatCurrency(item.budget)}
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      item.percentage_used >= 100
                        ? "bg-red-500"
                        : item.percentage_used >= 90
                          ? "bg-amber-500"
                          : "bg-emerald-500"
                    }`}
                    style={{ width: `${Math.min(100, item.percentage_used)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  {item.percentage_used.toFixed(0)}% used ·{" "}
                  {Number(item.remaining) >= 0
                    ? `${formatCurrency(item.remaining)} remaining`
                    : `${formatCurrency(Math.abs(Number(item.remaining)))} over`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {budgets && budgets.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              All Budgets
            </p>
          </div>
          <div className="divide-y divide-gray-100">
            {budgets.map((b) => (
              <div key={b.id}>
                <div className="px-4 pt-2 pb-0">
                  <p className="text-xs font-semibold text-gray-600">
                    {categoryMap.get(b.category_id)?.name ?? b.category_id}
                  </p>
                </div>
                <BudgetRow
                  budget={b}
                  onDelete={() => {
                    if (window.confirm("Delete this budget?")) removeBudget.mutate(b.id)
                  }}
                />
              </div>
            ))}
          </div>
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
