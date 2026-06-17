import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { membersApi } from "@/api/members"
import { useAuth } from "@/hooks/useAuth"

interface Widget {
  id: string
  label: string
  visible: boolean
  order: number
}

const DEFAULT_WIDGETS: Widget[] = [
  {
    id: "metric_cards",
    label: "KPI Cards (Net Worth, Income, Expenses, Savings Rate)",
    visible: true,
    order: 0,
  },
  { id: "budget_alerts", label: "Budget Alerts", visible: true, order: 1 },
  { id: "net_worth_chart", label: "Net Worth Chart (12 months)", visible: true, order: 2 },
  { id: "spending_chart", label: "Spending by Category", visible: true, order: 3 },
]

export default function SettingsDashboard() {
  const queryClient = useQueryClient()
  const memberId = useAuth((s) => s.memberId)

  const { data: member } = useQuery({
    queryKey: ["members", memberId],
    queryFn: () => membersApi.get(memberId!),
    enabled: Boolean(memberId),
  })

  const savedWidgets = (member?.settings?.dashboard_widgets ?? []) as Widget[]

  const [widgets, setWidgets] = useState<Widget[]>(() => {
    const base = savedWidgets.length > 0 ? savedWidgets : DEFAULT_WIDGETS
    return DEFAULT_WIDGETS.map((d) => base.find((w) => w.id === d.id) ?? d).sort(
      (a, b) => a.order - b.order,
    )
  })

  const save = useMutation({
    mutationFn: (ws: Widget[]) =>
      membersApi.updateDashboardLayout(memberId!, {
        widgets: ws.map(({ id, visible, order }) => ({ id, visible, order })),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["members", memberId] }),
  })

  function toggle(id: string) {
    setWidgets((ws) => ws.map((w) => (w.id === id ? { ...w, visible: !w.visible } : w)))
  }

  function moveUp(idx: number) {
    if (idx === 0) return
    setWidgets((ws) => {
      const next = [...ws]
      ;[next[idx - 1], next[idx]] = [next[idx], next[idx - 1]]
      return next.map((w, i) => ({ ...w, order: i }))
    })
  }

  function moveDown(idx: number) {
    setWidgets((ws) => {
      if (idx === ws.length - 1) return ws
      const next = [...ws]
      ;[next[idx], next[idx + 1]] = [next[idx + 1], next[idx]]
      return next.map((w, i) => ({ ...w, order: i }))
    })
  }

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
          Dashboard Layout
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Choose which widgets appear on your dashboard and in what order.
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
        {widgets.map((w, i) => (
          <div key={w.id} className="flex items-center gap-4 px-5 py-4">
            <div className="flex flex-col gap-0.5">
              <button
                onClick={() => moveUp(i)}
                disabled={i === 0}
                className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30 text-xs leading-none"
                aria-label="Move up"
              >
                ▲
              </button>
              <button
                onClick={() => moveDown(i)}
                disabled={i === widgets.length - 1}
                className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30 text-xs leading-none"
                aria-label="Move down"
              >
                ▼
              </button>
            </div>
            <span className="flex-1 text-sm text-gray-900 dark:text-gray-100">{w.label}</span>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {w.visible ? "Visible" : "Hidden"}
              </span>
              <input
                type="checkbox"
                checked={w.visible}
                onChange={() => toggle(w.id)}
                className="h-4 w-4 accent-indigo-600"
              />
            </label>
          </div>
        ))}
      </div>

      <button
        onClick={() => save.mutate(widgets)}
        disabled={save.isPending}
        className="px-5 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
      >
        {save.isPending ? "Saving…" : "Save layout"}
      </button>
      {save.isSuccess && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400">Layout saved.</p>
      )}
    </div>
  )
}
