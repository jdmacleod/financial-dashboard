import { useState } from "react"
import { useParams, useNavigate } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { fireApi } from "@/api/fire"
import { formatCurrency } from "@/lib/formatters"
import type { IncomeStream } from "@/api/types"

const INCOME_STREAM_TYPE_LABELS: Record<string, string> = {
  salary: "Salary",
  rental: "Rental",
  consulting: "Consulting",
  pension: "Pension",
  social_security: "Social Security",
  investment: "Investment",
  other: "Other",
}

const scenarioSchema = z.object({
  name: z.string().min(1),
  target_annual_spend: z.string().min(1),
  safe_withdrawal_rate: z.string().min(1),
  expected_annual_return: z.string().min(1),
  expected_inflation_rate: z.string().min(1),
  target_retirement_age: z.string().optional(),
})
type ScenarioForm = z.infer<typeof scenarioSchema>

const streamSchema = z.object({
  label: z.string().min(1),
  type: z.string().min(1),
  amount_annual: z.string().min(1),
  growth_rate_annual: z.string(),
  start_year: z.string(),
  end_year: z.string().optional(),
  is_pre_retirement: z.boolean(),
})
type StreamForm = z.infer<typeof streamSchema>

function StreamTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    salary: "bg-blue-100 text-blue-700",
    rental: "bg-green-100 text-green-700",
    consulting: "bg-yellow-100 text-yellow-700",
    pension: "bg-purple-100 text-purple-700",
    social_security: "bg-gray-100 text-gray-700",
    investment: "bg-indigo-100 text-indigo-700",
    other: "bg-gray-100 text-gray-600",
  }
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[type] ?? colors.other}`}
    >
      {INCOME_STREAM_TYPE_LABELS[type] ?? type}
    </span>
  )
}

function AddStreamModal({
  onAdd,
  onClose,
}: {
  onAdd: (stream: IncomeStream) => void
  onClose: () => void
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<StreamForm>({
    resolver: zodResolver(streamSchema),
    defaultValues: {
      growth_rate_annual: "0.03",
      start_year: String(new Date().getFullYear()),
      is_pre_retirement: true,
    },
  })

  function onSubmit(data: StreamForm) {
    const stream: IncomeStream = {
      id: crypto.randomUUID(),
      label: data.label,
      type: data.type as IncomeStream["type"],
      amount_annual: data.amount_annual,
      growth_rate_annual: data.growth_rate_annual || "0.03",
      start_year: parseInt(data.start_year) || new Date().getFullYear(),
      end_year: data.end_year ? parseInt(data.end_year) : null,
      is_pre_retirement: data.is_pre_retirement,
      notes: null,
      real_estate_property_id: null,
      source_account_id: null,
      auto_detected: false,
      detected_at: null,
    }
    onAdd(stream)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Add Income Stream</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Label</label>
            <input
              {...register("label")}
              placeholder="e.g. Day job salary"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.label && <p className="text-xs text-red-600">{errors.label.message}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
            <select
              {...register("type")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {Object.entries(INCOME_STREAM_TYPE_LABELS).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Annual amount</label>
              <input
                {...register("amount_annual")}
                placeholder="60000"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Growth rate</label>
              <input
                {...register("growth_rate_annual")}
                placeholder="0.03"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Start year</label>
              <input
                {...register("start_year")}
                type="number"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                End year (blank = indefinite)
              </label>
              <input
                {...register("end_year")}
                type="number"
                placeholder="none"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" {...register("is_pre_retirement")} />
            Pre-retirement income (contributes to savings)
          </label>
          <button
            type="submit"
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Add Stream
          </button>
        </form>
      </div>
    </div>
  )
}

export default function FireDetail() {
  const { scenarioId } = useParams({ strict: false }) as { scenarioId: string }
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showAddStream, setShowAddStream] = useState(false)
  const [detectError, setDetectError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const { data: scenario, isLoading } = useQuery({
    queryKey: ["fire-scenario", scenarioId],
    queryFn: () => fireApi.get(scenarioId),
  })

  const { data: projection, isLoading: projLoading } = useQuery({
    queryKey: ["fire-projection", scenarioId],
    queryFn: () => fireApi.projection(scenarioId),
    enabled: !!scenario,
  })

  const {
    register,
    handleSubmit,
    formState: { isDirty, isSubmitting },
    reset,
  } = useForm<ScenarioForm>({
    resolver: zodResolver(scenarioSchema),
    values: scenario
      ? {
          name: scenario.name,
          target_annual_spend: scenario.target_annual_spend,
          safe_withdrawal_rate: scenario.safe_withdrawal_rate,
          expected_annual_return: scenario.expected_annual_return,
          expected_inflation_rate: scenario.expected_inflation_rate,
          target_retirement_age: scenario.target_retirement_age
            ? String(scenario.target_retirement_age)
            : "",
        }
      : undefined,
  })

  const updateMutation = useMutation({
    mutationFn: (data: ScenarioForm) =>
      fireApi.update(scenarioId, {
        name: data.name,
        target_annual_spend: data.target_annual_spend,
        safe_withdrawal_rate: data.safe_withdrawal_rate,
        expected_annual_return: data.expected_annual_return,
        expected_inflation_rate: data.expected_inflation_rate,
        target_retirement_age: data.target_retirement_age
          ? parseInt(data.target_retirement_age)
          : null,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["fire-scenario", scenarioId], updated)
      queryClient.invalidateQueries({ queryKey: ["fire-projection", scenarioId] })
      reset({
        name: updated.name,
        target_annual_spend: updated.target_annual_spend,
        safe_withdrawal_rate: updated.safe_withdrawal_rate,
        expected_annual_return: updated.expected_annual_return,
        expected_inflation_rate: updated.expected_inflation_rate,
        target_retirement_age: updated.target_retirement_age
          ? String(updated.target_retirement_age)
          : "",
      })
    },
    onError: () => setSaveError("Failed to save changes."),
  })

  const detectMutation = useMutation({
    mutationFn: () => fireApi.detect(scenarioId),
    onSuccess: (result) => {
      queryClient.setQueryData(["fire-scenario", scenarioId], result.scenario)
      queryClient.invalidateQueries({ queryKey: ["fire-projection", scenarioId] })
      setDetectError(null)
    },
    onError: () => setDetectError("Detection failed."),
  })

  const deleteMutation = useMutation({
    mutationFn: () => fireApi.delete(scenarioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fire-scenarios"] })
      void navigate({ to: "/fire" })
    },
  })

  function handleAddStream(stream: IncomeStream) {
    if (!scenario) return
    const updated = [...scenario.additional_income_streams, stream]
    void fireApi.update(scenarioId, { additional_income_streams: updated }).then((res) => {
      queryClient.setQueryData(["fire-scenario", scenarioId], res)
      queryClient.invalidateQueries({ queryKey: ["fire-projection", scenarioId] })
    })
  }

  function handleRemoveStream(streamId: string) {
    if (!scenario) return
    const updated = scenario.additional_income_streams.filter((s) => s.id !== streamId)
    void fireApi.update(scenarioId, { additional_income_streams: updated }).then((res) => {
      queryClient.setQueryData(["fire-scenario", scenarioId], res)
      queryClient.invalidateQueries({ queryKey: ["fire-projection", scenarioId] })
    })
  }

  if (isLoading) return <div className="p-8 text-gray-500">Loading…</div>
  if (!scenario) return <div className="p-8 text-red-600">Scenario not found.</div>

  const chartData = projection?.projections.map((p) => ({
    year: p.year,
    age: p.age,
    Portfolio: Number(p.portfolio),
    "FIRE Number": Number(p.fire_number),
  }))

  const fireYear = projection?.summary.fire_year

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <a href="/fire" className="text-sm text-indigo-600 hover:underline">
            ← FIRE Scenarios
          </a>
          <h1 className="text-2xl font-semibold mt-1">{scenario.name}</h1>
        </div>
        <button
          onClick={() => deleteMutation.mutate()}
          className="text-sm text-red-600 hover:underline"
        >
          Delete scenario
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left panel: editor */}
        <div className="space-y-5">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Scenario Settings</h2>
            <form
              onSubmit={handleSubmit((d) => {
                setSaveError(null)
                updateMutation.mutate(d)
              })}
              className="space-y-3"
            >
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Name</label>
                <input
                  {...register("name")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Target annual spend (today's dollars)
                </label>
                <input
                  {...register("target_annual_spend")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">SWR</label>
                  <input
                    {...register("safe_withdrawal_rate")}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Expected return
                  </label>
                  <input
                    {...register("expected_annual_return")}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Inflation</label>
                  <input
                    {...register("expected_inflation_rate")}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Target retirement age (optional)
                </label>
                <input
                  {...register("target_retirement_age")}
                  type="number"
                  placeholder="e.g. 55"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              {saveError && (
                <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {saveError}
                </p>
              )}
              {isDirty && (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                  {isSubmitting ? "Saving…" : "Save Changes"}
                </button>
              )}
            </form>
          </div>

          {/* Income Streams */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-gray-700">Income Streams</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setDetectError(null)
                    detectMutation.mutate()
                  }}
                  disabled={detectMutation.isPending}
                  className="text-xs rounded-lg border border-gray-200 px-3 py-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-60"
                >
                  {detectMutation.isPending ? "Detecting…" : "Auto-detect"}
                </button>
                <button
                  onClick={() => setShowAddStream(true)}
                  className="text-xs rounded-lg bg-indigo-600 px-3 py-1.5 text-white hover:bg-indigo-700"
                >
                  Add stream
                </button>
              </div>
            </div>

            {detectMutation.data?.warnings && detectMutation.data.warnings.length > 0 && (
              <div className="mb-3 bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 space-y-1">
                {detectMutation.data.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-yellow-800">
                    {w}
                  </p>
                ))}
              </div>
            )}

            {detectError && (
              <p className="mb-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                {detectError}
              </p>
            )}

            {scenario.additional_income_streams.length === 0 ? (
              <p className="text-sm text-gray-400 py-4 text-center">
                No income streams yet. Add streams or use auto-detect.
              </p>
            ) : (
              <div className="space-y-2">
                {scenario.additional_income_streams.map((stream) => (
                  <div
                    key={stream.id}
                    className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 bg-gray-50"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <StreamTypeBadge type={stream.type} />
                      <span className="text-sm text-gray-900 truncate">{stream.label}</span>
                      {stream.auto_detected && (
                        <span className="text-xs text-gray-400 shrink-0">Detected</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 ml-2 shrink-0">
                      <span className="text-sm font-medium text-gray-900">
                        {formatCurrency(stream.amount_annual)}/yr
                      </span>
                      <button
                        onClick={() => handleRemoveStream(stream.id)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right panel: projection */}
        <div className="space-y-5">
          {projection && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="mb-3">
                <p className="text-sm font-semibold text-gray-700">FIRE Projection</p>
                <p className="text-lg font-semibold text-indigo-600 mt-0.5">
                  {projection.summary.headline}
                </p>
                <p className="text-xs text-gray-500">
                  FIRE number: {formatCurrency(projection.summary.fire_number)}
                </p>
              </div>

              {chartData && chartData.length > 0 && (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={chartData}>
                    <XAxis
                      dataKey="year"
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
                    <Tooltip
                      formatter={(v, name) => [formatCurrency(v as number), name as string]}
                    />
                    <Line
                      type="monotone"
                      dataKey="Portfolio"
                      stroke="#6366f1"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="FIRE Number"
                      stroke="#ef4444"
                      strokeWidth={1.5}
                      strokeDasharray="6 3"
                      dot={false}
                    />
                    {fireYear && (
                      <ReferenceLine
                        x={fireYear}
                        stroke="#10b981"
                        strokeDasharray="4 2"
                        label={{
                          value: `FIRE ${fireYear}`,
                          position: "insideTopLeft",
                          fontSize: 11,
                          fill: "#10b981",
                        }}
                      />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          )}

          {projLoading && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-sm text-gray-400">Calculating projection…</p>
            </div>
          )}

          {projection && projection.projections.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">
                      Year
                    </th>
                    {projection.projections[0].age !== null && (
                      <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">
                        Age
                      </th>
                    )}
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">
                      Portfolio
                    </th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">
                      Income
                    </th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500">
                      Savings
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {projection.projections.slice(0, 10).map((p) => (
                    <tr key={p.year} className={p.is_fire_year ? "bg-emerald-50" : ""}>
                      <td className="px-3 py-2 text-gray-600">
                        {p.year}
                        {p.is_fire_year && (
                          <span className="ml-1 text-xs text-emerald-600 font-medium">FIRE</span>
                        )}
                      </td>
                      {p.age !== null && <td className="px-3 py-2 text-gray-500">{p.age}</td>}
                      <td className="px-3 py-2 text-right font-medium text-gray-900">
                        {formatCurrency(p.portfolio)}
                      </td>
                      <td className="px-3 py-2 text-right text-emerald-600">
                        {formatCurrency(p.annual_income)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-medium ${Number(p.annual_savings) >= 0 ? "text-indigo-600" : "text-red-600"}`}
                      >
                        {formatCurrency(p.annual_savings)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {projection.projections.length > 10 && (
                <p className="text-xs text-gray-400 text-center py-2">
                  Showing first 10 of {projection.projections.length} years
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {showAddStream && (
        <AddStreamModal onAdd={handleAddStream} onClose={() => setShowAddStream(false)} />
      )}
    </div>
  )
}
