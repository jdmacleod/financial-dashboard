import { Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts"
import { reportsApi } from "@/api/reports"
import { membersApi } from "@/api/members"
import { useAuth } from "@/hooks/useAuth"
import { formatCurrency } from "@/lib/formatters"
import { lastNMonthsRange } from "@/lib/dateRange"

const CHART_COLORS = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
]

interface WidgetConfig {
  id: string
  visible: boolean
  order: number
}

const DEFAULT_WIDGET_ORDER = ["metric_cards", "budget_alerts", "net_worth_chart", "spending_chart"]

function useWidgetConfig(): WidgetConfig[] {
  const memberId = useAuth((s) => s.memberId)
  const { data: member } = useQuery({
    queryKey: ["members", memberId],
    queryFn: () => membersApi.get(memberId!),
    enabled: Boolean(memberId),
  })
  const saved = (member?.settings?.dashboard_widgets ?? []) as WidgetConfig[]
  if (saved.length === 0) {
    return DEFAULT_WIDGET_ORDER.map((id, order) => ({ id, visible: true, order }))
  }
  return [...saved].sort((a, b) => a.order - b.order)
}

function MetricCard({
  label,
  value,
  sub,
  color = "text-gray-900 dark:text-gray-100",
}: {
  label: string
  value: string
  sub?: string
  color?: string
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{label}</p>
      <p className={`text-2xl font-semibold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const widgets = useWidgetConfig()

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: reportsApi.dashboard,
  })

  const range = lastNMonthsRange(12)
  const { data: nwReport } = useQuery({
    queryKey: ["reports", "net-worth", range],
    queryFn: () => reportsApi.netWorth(range.from, range.to, "monthly"),
  })

  if (isLoading)
    return <div className="p-8 text-gray-500 dark:text-gray-400">Loading dashboard…</div>
  if (error || !data)
    return <div className="p-8 text-red-600 dark:text-red-400">Failed to load dashboard.</div>

  const nwChange = Number(data.net_worth.change_30d)
  const nwColor =
    nwChange >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"
  const savingsRate =
    Number(data.cash_flow_mtd.income) > 0
      ? ((Number(data.cash_flow_mtd.net) / Number(data.cash_flow_mtd.income)) * 100).toFixed(1)
      : null

  const nwChartData = nwReport?.series.map((p) => ({
    date: p.date.slice(0, 7),
    "Net Worth": Number(p.net_worth),
    Assets: Number(p.total_assets),
    Liabilities: -Number(p.total_liabilities),
  }))

  const pieData = data.top_spending_categories.map((c) => ({
    name: c.name,
    value: Math.abs(Number(c.amount)),
  }))

  const sections = widgets.filter((w) => w.visible).map((w) => w.id)

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Dashboard</h1>
        <Link
          to="/settings/dashboard"
          className="text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
        >
          Customize →
        </Link>
      </div>

      {sections.includes("metric_cards") && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <MetricCard
            label="Net Worth"
            value={formatCurrency(data.net_worth.current)}
            sub={
              data.net_worth.change_30d_pct != null
                ? `${nwChange >= 0 ? "+" : ""}${data.net_worth.change_30d_pct.toFixed(1)}% vs 30d ago`
                : undefined
            }
            color={nwColor}
          />
          <MetricCard
            label="MTD Income"
            value={formatCurrency(data.cash_flow_mtd.income)}
            color="text-emerald-600 dark:text-emerald-400"
          />
          <MetricCard
            label="MTD Expenses"
            value={formatCurrency(data.cash_flow_mtd.expenses)}
            color="text-red-600 dark:text-red-400"
          />
          <MetricCard
            label="Savings Rate"
            value={savingsRate != null ? `${savingsRate}%` : "—"}
            sub="month to date"
          />
        </div>
      )}

      {sections.includes("budget_alerts") && data.budget_alerts.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Budget Alerts
          </h2>
          <div className="flex flex-wrap gap-2">
            {data.budget_alerts.map((a) => (
              <Link
                key={a.category}
                to="/budgets"
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                  a.used_pct >= 100 ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                }`}
              >
                {a.category}
                <span className="font-semibold">{a.used_pct.toFixed(0)}%</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {(sections.includes("net_worth_chart") || sections.includes("spending_chart")) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {sections.includes("net_worth_chart") && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Net Worth (12 months)
                </h2>
                <Link
                  to="/reports/net-worth"
                  className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Full report →
                </Link>
              </div>
              {nwChartData && nwChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={nwChartData}>
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) =>
                        v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                      }
                    />
                    <Tooltip formatter={(v) => formatCurrency(v as number)} />
                    <Line
                      type="monotone"
                      dataKey="Net Worth"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
                  No data yet.
                </p>
              )}
            </div>
          )}

          {sections.includes("spending_chart") && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                  Spending This Month
                </h2>
                <Link
                  to="/reports/spending"
                  className="text-xs text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Full report →
                </Link>
              </div>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatCurrency(v as number)} />
                    <Legend iconType="circle" iconSize={8} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
                  No spending data yet.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
