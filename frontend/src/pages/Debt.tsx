import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { debtApi } from "@/api/debt"
import { formatCurrency } from "@/lib/formatters"
import type { DebtPayoffPlanResponse, DebtWithAccountResponse } from "@/api/types"

function DebtSummaryCard({ debt }: { debt: DebtWithAccountResponse }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-gray-900">{debt.nickname}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {(Number(debt.interest_rate) * 100).toFixed(2)}% APR
          </p>
        </div>
        <div className="text-right">
          <p className="font-semibold text-gray-900">{formatCurrency(debt.current_balance)}</p>
          <p className="text-xs text-gray-500">Min: {formatCurrency(debt.minimum_payment)}/mo</p>
        </div>
      </div>
    </div>
  )
}

function PayoffPlanCard({ plan }: { plan: DebtPayoffPlanResponse }) {
  const isAvalanche = plan.strategy === "avalanche"
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`px-2 py-0.5 rounded text-xs font-semibold ${isAvalanche ? "bg-indigo-100 text-indigo-700" : "bg-emerald-100 text-emerald-700"}`}
        >
          {isAvalanche ? "Avalanche" : "Snowball"}
        </span>
        <span className="text-xs text-gray-500">
          {isAvalanche ? "Highest rate first" : "Lowest balance first"}
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Months to payoff</span>
          <span className="font-medium">{plan.months_to_payoff}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Total interest</span>
          <span className="font-medium text-red-600">
            {formatCurrency(plan.total_interest_paid)}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Payoff date</span>
          <span className="font-medium">{plan.payoff_date}</span>
        </div>
        {plan.payoff_order.length > 0 && (
          <div className="pt-2">
            <p className="text-xs text-gray-500 mb-1">Payoff order:</p>
            <div className="flex flex-wrap gap-1">
              {plan.payoff_order.map((name, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-700"
                >
                  <span className="text-gray-400">{i + 1}.</span> {name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Debt() {
  // Stored as a string so the field can be empty (no forced leading "0"); parsed
  // to a number for the query and comparisons.
  const [extraPayment, setExtraPayment] = useState("")
  const extra = Number(extraPayment) || 0

  const { data, isLoading } = useQuery({
    queryKey: ["debt-payoff", extra],
    queryFn: () => debtApi.payoffComparison(extra),
  })

  // Build chart data from avalanche monthly_series (sample every few months)
  const avalancheChart = data?.avalanche.monthly_series
    .filter((_, i) => i % 6 === 0 || i === (data?.avalanche.monthly_series.length ?? 0) - 1)
    .map((m) => {
      const point: Record<string, number | string> = { date: m.date.slice(0, 7) }
      data.debts.forEach((d) => {
        point[d.nickname] = Number(m.per_debt[d.debt_id] ?? 0)
      })
      return point
    })

  const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Debt Payoff</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Compare avalanche vs snowball payoff strategies
        </p>
      </div>

      {/* Extra payment input */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4">
        <label
          htmlFor="extra-monthly-payment"
          className="text-sm font-medium text-gray-700 whitespace-nowrap"
        >
          Extra monthly payment:
        </label>
        <div className="flex items-center gap-2">
          <span className="text-gray-400">$</span>
          <input
            id="extra-monthly-payment"
            type="number"
            min={0}
            value={extraPayment}
            onChange={(e) => setExtraPayment(e.target.value)}
            placeholder="0"
            className="w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        {extra > 0 && (
          <span className="text-xs text-gray-400">Applied to target debt after minimums</span>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading…</p>}

      {data && (
        <>
          {/* Debt list */}
          {data.debts.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
              <p className="text-gray-500">No debts found.</p>
              <p className="text-sm text-gray-400 mt-1">
                Add debt accounts and their details to see payoff projections.
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.debts.map((d) => (
                  <DebtSummaryCard key={d.debt_id} debt={d} />
                ))}
              </div>

              {/* Strategy comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <PayoffPlanCard plan={data.avalanche} />
                <PayoffPlanCard plan={data.snowball} />
              </div>

              {/* Comparison callout */}
              {Number(data.avalanche.total_interest_paid) <
                Number(data.snowball.total_interest_paid) && (
                <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 text-sm text-indigo-800">
                  Avalanche saves{" "}
                  <strong>
                    {formatCurrency(
                      String(
                        Number(data.snowball.total_interest_paid) -
                          Number(data.avalanche.total_interest_paid),
                      ),
                    )}
                  </strong>{" "}
                  in interest compared to snowball.
                </div>
              )}

              {/* Balance over time chart */}
              {avalancheChart && avalancheChart.length > 1 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-sm font-semibold text-gray-700 mb-3">
                    Balance Over Time (Avalanche)
                  </p>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={avalancheChart}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
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
                        tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                      />
                      <Tooltip formatter={(v) => formatCurrency(v as number)} />
                      {data.debts.map((d, i) => (
                        <Area
                          key={d.debt_id}
                          type="monotone"
                          dataKey={d.nickname}
                          stackId="1"
                          stroke={COLORS[i % COLORS.length]}
                          fill={COLORS[i % COLORS.length]}
                          fillOpacity={0.4}
                        />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
