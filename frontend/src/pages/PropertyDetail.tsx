import { useState } from "react"
import { useParams } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
} from "recharts"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { propertiesApi } from "@/api/properties"
import { reportsApi } from "@/api/reports"
import { formatCurrency } from "@/lib/formatters"
import { lastNMonthsRange } from "@/lib/dateRange"
import { HistoryPanel } from "@/components/app/HistoryPanel"

type Tab = "valuations" | "pnl" | "history"

const valuationSchema = z.object({
  valuation_date: z.string().min(1, "Required"),
  estimated_value: z.string().min(1, "Required"),
})
type ValuationForm = z.infer<typeof valuationSchema>

function AddValuationModal({ propertyId, onClose }: { propertyId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ValuationForm>({
    resolver: zodResolver(valuationSchema),
  })

  const add = useMutation({
    mutationFn: (data: ValuationForm) =>
      propertiesApi.addValuation(propertyId, {
        valuation_date: data.valuation_date,
        estimated_value: data.estimated_value,
        source: "manual",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["property", propertyId] })
      queryClient.invalidateQueries({ queryKey: ["property-valuations", propertyId] })
      onClose()
    },
    onError: () => setError("Failed to add valuation."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Update Valuation</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => add.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
            <input
              type="date"
              {...register("valuation_date")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.valuation_date && (
              <p className="mt-1 text-xs text-red-600">{errors.valuation_date.message}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Estimated value</label>
            <input
              {...register("estimated_value")}
              placeholder="e.g. 450000.00"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.estimated_value && (
              <p className="mt-1 text-xs text-red-600">{errors.estimated_value.message}</p>
            )}
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
            {isSubmitting ? "Saving…" : "Save Valuation"}
          </button>
        </form>
      </div>
    </div>
  )
}

export default function PropertyDetail() {
  const { propertyId } = useParams({ strict: false }) as { propertyId: string }
  const [tab, setTab] = useState<Tab>("valuations")
  const [showAddValuation, setShowAddValuation] = useState(false)

  const range = lastNMonthsRange(12)

  const { data: property, isLoading: propLoading } = useQuery({
    queryKey: ["property", propertyId],
    queryFn: () => propertiesApi.get(propertyId),
  })

  const { data: valuations } = useQuery({
    queryKey: ["property-valuations", propertyId],
    queryFn: () => propertiesApi.listValuations(propertyId),
    enabled: tab === "valuations",
  })

  const { data: pnl, isLoading: pnlLoading } = useQuery({
    queryKey: ["reports", "property-pnl", propertyId, range],
    queryFn: () => reportsApi.propertyPnl(propertyId, range.from, range.to),
    enabled: tab === "pnl",
  })

  if (propLoading) return <div className="p-8 text-gray-500">Loading…</div>
  if (!property) return <div className="p-8 text-red-600">Property not found.</div>

  const valuationChartData = valuations
    ?.slice()
    .sort((a, b) => a.valuation_date.localeCompare(b.valuation_date))
    .map((v) => ({ date: v.valuation_date.slice(0, 7), Value: Number(v.estimated_value) }))

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{property.nickname}</h1>
        <p className="text-sm text-gray-500">{property.address}</p>
        {property.current_estimated_value && (
          <p className="text-lg font-medium text-indigo-600 mt-1">
            {formatCurrency(property.current_estimated_value)}
            {property.current_value_as_of && (
              <span className="text-sm text-gray-400 font-normal ml-2">
                as of {property.current_value_as_of}
              </span>
            )}
          </p>
        )}
      </div>

      <div className="flex gap-1 border-b border-gray-200">
        {(
          [
            { key: "valuations", label: "Valuation History" },
            { key: "pnl", label: "P&L" },
            { key: "history", label: "Change History" },
          ] as { key: Tab; label: string }[]
        ).map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "valuations" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => setShowAddValuation(true)}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Update manually
            </button>
          </div>

          {valuationChartData && valuationChartData.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={valuationChartData}>
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Line
                    type="monotone"
                    dataKey="Value"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {valuations && valuations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">
                      Date
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                      Value
                    </th>
                    <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                      Source
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {[...valuations]
                    .sort((a, b) => b.valuation_date.localeCompare(a.valuation_date))
                    .map((v) => (
                      <tr key={v.id}>
                        <td className="px-4 py-2 text-gray-600">{v.valuation_date}</td>
                        <td className="px-4 py-2 text-right font-medium text-gray-900">
                          {formatCurrency(v.estimated_value)}
                        </td>
                        <td className="px-4 py-2 text-right text-gray-400 capitalize">
                          {v.source.replace("api_", "")}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          {(!valuations || valuations.length === 0) && (
            <p className="text-sm text-gray-400 py-8 text-center">No valuations yet.</p>
          )}
        </div>
      )}

      {tab === "pnl" && (
        <div className="space-y-4">
          {pnlLoading && <div className="text-sm text-gray-400">Loading P&L…</div>}
          {pnl && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Gross Income</p>
                  <p className="text-xl font-semibold text-emerald-600">
                    {formatCurrency(pnl.gross_income)}
                  </p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Total Expenses</p>
                  <p className="text-xl font-semibold text-red-600">
                    {formatCurrency(pnl.total_expenses)}
                  </p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Net Income</p>
                  <p
                    className={`text-xl font-semibold ${Number(pnl.net_income) >= 0 ? "text-indigo-600" : "text-red-600"}`}
                  >
                    {formatCurrency(pnl.net_income)}
                  </p>
                </div>
              </div>

              {pnl.expense_breakdown.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-sm font-semibold text-gray-700 mb-3">Expense Breakdown</p>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                      data={pnl.expense_breakdown.map((e) => ({
                        name: e.name,
                        Amount: Math.abs(Number(e.amount)),
                      }))}
                      layout="vertical"
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        width={100}
                      />
                      <Tooltip formatter={(v: number) => formatCurrency(v)} />
                      <Bar dataKey="Amount" fill="#6366f1" radius={[0, 3, 3, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {pnl.monthly_series.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500">
                          Month
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                          Income
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                          Expenses
                        </th>
                        <th className="px-4 py-2 text-right text-xs font-semibold text-gray-500">
                          Net
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {pnl.monthly_series.map((row) => (
                        <tr key={row.period}>
                          <td className="px-4 py-2 text-gray-600">{row.period}</td>
                          <td className="px-4 py-2 text-right text-emerald-600">
                            {formatCurrency(row.income)}
                          </td>
                          <td className="px-4 py-2 text-right text-red-600">
                            {formatCurrency(row.expenses)}
                          </td>
                          <td
                            className={`px-4 py-2 text-right font-medium ${Number(row.net) >= 0 ? "text-indigo-600" : "text-red-600"}`}
                          >
                            {formatCurrency(row.net)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {tab === "history" && (
        <HistoryPanel entityType="real_estate_property" entityId={propertyId} />
      )}

      {showAddValuation && (
        <AddValuationModal propertyId={propertyId} onClose={() => setShowAddValuation(false)} />
      )}
    </div>
  )
}
