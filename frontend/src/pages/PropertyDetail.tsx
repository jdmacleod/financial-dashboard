import { useState } from "react"
import { useParams } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
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
import { accountsApi } from "@/api/accounts"
import { propertiesApi } from "@/api/properties"
import { reportsApi } from "@/api/reports"
import { insurancePoliciesApi } from "@/api/insurancePolicies"
import type { PropertyResponse, PropertyType } from "@/api/types"
import { formatCurrency, formatDate } from "@/lib/formatters"
import { lastNMonthsRange } from "@/lib/dateRange"
import { HistoryPanel } from "@/components/app/HistoryPanel"
import { useOwnershipEntities } from "@/hooks/useOwnershipEntities"

const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  primary_residence: "Primary Residence",
  rental: "Rental Property",
  vacation: "Vacation Home",
  commercial: "Commercial",
  land: "Land",
  other: "Other",
}

const PROPERTY_TYPE_COLORS: Record<PropertyType, string> = {
  primary_residence: "bg-indigo-100 text-indigo-700",
  rental: "bg-emerald-100 text-emerald-700",
  vacation: "bg-sky-100 text-sky-700",
  commercial: "bg-amber-100 text-amber-700",
  land: "bg-stone-100 text-stone-700",
  other: "bg-gray-100 text-gray-600",
}

const editPropertySchema = z.object({
  address: z.string().min(1, "Address is required"),
  property_type: z.enum(["primary_residence", "rental", "vacation", "commercial", "land", "other"]),
  purchase_date: z.string().optional(),
  purchase_price: z.string().optional(),
  linked_mortgage_account_id: z.string().optional(),
  ownership_entity_id: z.string().nullable(),
})
type EditPropertyForm = z.infer<typeof editPropertySchema>

function EditPropertyModal({
  property,
  onClose,
}: {
  property: PropertyResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { data: allAccounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  })
  const mortgageAccounts =
    allAccounts?.filter((a) => a.account_type === "mortgage" && a.is_active) ?? []
  const { data: entities } = useOwnershipEntities()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EditPropertyForm>({
    resolver: zodResolver(editPropertySchema),
    defaultValues: {
      address: property.address,
      property_type: property.property_type,
      purchase_date: property.purchase_date ?? "",
      purchase_price: property.purchase_price ?? "",
      linked_mortgage_account_id: property.linked_mortgage_account_id ?? "",
      ownership_entity_id: property.ownership_entity_id,
    },
  })

  const update = useMutation({
    mutationFn: (data: EditPropertyForm) =>
      propertiesApi.update(property.id, {
        address: data.address,
        property_type: data.property_type as PropertyType,
        purchase_date: data.purchase_date || null,
        purchase_price: data.purchase_price || null,
        linked_mortgage_account_id: data.linked_mortgage_account_id || null,
        ownership_entity_id: data.ownership_entity_id || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["property", property.id] })
      queryClient.invalidateQueries({ queryKey: ["property-equity", property.id] })
      onClose()
    },
    onError: () => setError("Failed to save property details."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Edit property details</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => update.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
            <input
              {...register("address")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.address && (
              <p className="mt-1 text-xs text-red-600">{errors.address.message}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Property type</label>
            <select
              {...register("property_type")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {(Object.entries(PROPERTY_TYPE_LABELS) as [PropertyType, string][]).map(
                ([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ),
              )}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Purchase date</label>
              <input
                type="date"
                {...register("purchase_date")}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Purchase price</label>
              <input
                {...register("purchase_price")}
                placeholder="e.g. 350000.00"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Linked mortgage account
            </label>
            <select
              {...register("linked_mortgage_account_id")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">None</option>
              {mortgageAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nickname}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-400">
              Links this property to a mortgage for equity calculation.
            </p>
          </div>
          {entities && entities.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Titled to</label>
              <select
                {...register("ownership_entity_id")}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">Directly owned</option>
                {entities.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          <div className="flex gap-3 pt-2">
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

type Tab = "valuations" | "equity" | "pnl" | "history"

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

const POLICY_TYPE_LABELS: Record<string, string> = {
  term_life: "Term Life",
  permanent_life: "Permanent Life",
  umbrella_liability: "Umbrella Liability",
  disability: "Disability",
  long_term_care: "Long-Term Care",
  scheduled_specialty: "Scheduled / Specialty",
  homeowners: "Homeowners",
  renters: "Renters",
}

const CADENCE_LABELS: Record<string, string> = {
  monthly: "/mo",
  quarterly: "/qtr",
  annual: "/yr",
}

export default function PropertyDetail() {
  const { propertyId } = useParams({ strict: false }) as { propertyId: string }
  const [tab, setTab] = useState<Tab>("valuations")
  const [showAddValuation, setShowAddValuation] = useState(false)
  const [showEdit, setShowEdit] = useState(false)

  const range = lastNMonthsRange(12)

  const { data: property, isLoading: propLoading } = useQuery({
    queryKey: ["property", propertyId],
    queryFn: () => propertiesApi.get(propertyId),
  })

  const { data: allPolicies } = useQuery({
    queryKey: ["insurance-policies"],
    queryFn: insurancePoliciesApi.list,
  })

  const { data: valuations } = useQuery({
    queryKey: ["property-valuations", propertyId],
    queryFn: () => propertiesApi.listValuations(propertyId),
    enabled: tab === "valuations",
  })

  const {
    data: equity,
    isLoading: equityLoading,
    error: equityError,
  } = useQuery({
    queryKey: ["property-equity", propertyId],
    queryFn: () => propertiesApi.getEquity(propertyId),
    enabled: tab === "equity",
    retry: false,
  })

  const { data: pnl, isLoading: pnlLoading } = useQuery({
    queryKey: ["reports", "property-pnl", propertyId, range],
    queryFn: () => reportsApi.propertyPnl(propertyId, range.from, range.to),
    enabled: tab === "pnl",
  })

  if (propLoading) return <div className="p-8 text-gray-500">Loading…</div>
  if (!property) return <div className="p-8 text-red-600">Property not found.</div>

  const gainLoss = property.gain_loss !== null ? Number(property.gain_loss) : null
  const gainLossPct = property.gain_loss_pct !== null ? Number(property.gain_loss_pct) : null

  const linkedPolicies = allPolicies?.filter((p) => p.insured_real_estate_id === propertyId) ?? []

  const valuationChartData = valuations
    ?.slice()
    .sort((a, b) => a.valuation_date.localeCompare(b.valuation_date))
    .map((v) => ({ date: v.valuation_date.slice(0, 7), Value: Number(v.estimated_value) }))

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-semibold">{property.nickname}</h1>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${PROPERTY_TYPE_COLORS[property.property_type as PropertyType]}`}
            >
              {PROPERTY_TYPE_LABELS[property.property_type as PropertyType]}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{property.address}</p>
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
          {property.purchase_price && (
            <p className="text-sm text-gray-500 mt-0.5">
              {property.purchase_date && `Purchased ${formatDate(property.purchase_date)} · `}
              Paid {formatCurrency(property.purchase_price)}
              {gainLoss !== null && (
                <span
                  className={`ml-2 font-medium ${gainLoss >= 0 ? "text-emerald-600" : "text-red-600"}`}
                >
                  {gainLoss >= 0 ? "+" : ""}
                  {formatCurrency(String(Math.abs(gainLoss)))}
                  {gainLossPct !== null && (
                    <>
                      {" "}
                      ({gainLoss >= 0 ? "+" : ""}
                      {gainLossPct.toFixed(1)}%)
                    </>
                  )}
                </span>
              )}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowEdit(true)}
          className="shrink-0 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Edit details
        </button>
      </div>

      {linkedPolicies.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Insurance
          </p>
          <div className="space-y-2">
            {linkedPolicies.map((pol) => (
              <div key={pol.id} className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <span className="text-sm font-medium text-gray-800">
                    {POLICY_TYPE_LABELS[pol.policy_type] ?? pol.policy_type}
                  </span>
                  {pol.carrier && (
                    <span className="ml-2 text-xs text-gray-500">
                      {pol.carrier}
                      {pol.policy_number && (
                        <span className="ml-1 font-mono opacity-75">#{pol.policy_number}</span>
                      )}
                    </span>
                  )}
                  {pol.technical_notes && (
                    <p className="text-xs text-gray-400 italic mt-0.5">{pol.technical_notes}</p>
                  )}
                </div>
                <div className="text-right flex-shrink-0">
                  <span className="text-sm text-gray-700">
                    {formatCurrency(pol.coverage_amount)}
                  </span>
                  <span className="text-xs text-gray-400 ml-1">coverage</span>
                  <p className="text-xs text-gray-400">
                    {formatCurrency(pol.premium_amount)}
                    {CADENCE_LABELS[pol.premium_cadence] ?? ""}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1 border-b border-gray-200">
        {(
          [
            { key: "valuations", label: "Valuation History" },
            { key: "equity", label: "Equity" },
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
                  <Tooltip formatter={(v) => formatCurrency(v as number)} />
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

      {tab === "equity" && (
        <div className="space-y-4">
          {equityLoading && (
            <div className="grid grid-cols-3 gap-4">
              {[0, 1, 2].map((i) => (
                <div key={i} className="bg-gray-100 rounded-xl h-24 animate-pulse" />
              ))}
            </div>
          )}

          {!equityLoading && (equityError as { status?: number } | null)?.status === 404 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-base mb-1">No valuation available</p>
              <p className="text-sm">Add a valuation to calculate equity.</p>
            </div>
          )}

          {equity && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Property Value</p>
                  <p className="text-xl font-semibold text-gray-900">
                    {formatCurrency(equity.property_value)}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    as of {equity.valuation_date} · {equity.valuation_source.replace("api_", "")}
                  </p>
                </div>

                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Mortgage Balance</p>
                  {!equity.mortgage_balance_visible ? (
                    <p className="text-sm text-gray-400 mt-1">Not visible</p>
                  ) : equity.mortgage_balance !== null ? (
                    <>
                      <p className="text-xl font-semibold text-gray-900">
                        {formatCurrency(equity.mortgage_balance)}
                      </p>
                      {equity.mortgage_balance_as_of && (
                        <p className="text-xs text-gray-400 mt-1">
                          as of {equity.mortgage_balance_as_of}
                        </p>
                      )}
                    </>
                  ) : property.linked_mortgage_account_id ? (
                    <p className="text-sm text-gray-400 mt-1">Linked · no balance recorded yet</p>
                  ) : (
                    <p className="text-sm text-gray-400 mt-1">No mortgage linked</p>
                  )}
                </div>

                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-500 mb-1">Equity</p>
                  {equity.equity !== null ? (
                    <p
                      className={`text-xl font-semibold ${
                        Number(equity.equity) < 0 ? "text-red-600" : "text-indigo-600"
                      }`}
                    >
                      {formatCurrency(equity.equity)}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400 mt-1">—</p>
                  )}
                </div>
              </div>
            </>
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
                      <Tooltip formatter={(v) => formatCurrency(v as number)} />
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
      {showEdit && <EditPropertyModal property={property} onClose={() => setShowEdit(false)} />}
    </div>
  )
}
