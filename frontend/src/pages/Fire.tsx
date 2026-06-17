import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { fireApi } from "@/api/fire"
import { formatCurrency } from "@/lib/formatters"
import type { FireScenarioResponse } from "@/api/types"

const createSchema = z.object({
  name: z.string().min(1, "Name is required").max(100),
  target_annual_spend: z.string().min(1, "Required"),
  safe_withdrawal_rate: z.string().optional(),
  target_retirement_age: z.string().optional(),
})

type CreateForm = z.infer<typeof createSchema>

function NewScenarioModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({ resolver: zodResolver(createSchema) })

  const create = useMutation({
    mutationFn: (data: CreateForm) =>
      fireApi.create({
        name: data.name,
        target_annual_spend: data.target_annual_spend,
        safe_withdrawal_rate: data.safe_withdrawal_rate || undefined,
        target_retirement_age: data.target_retirement_age
          ? parseInt(data.target_retirement_age)
          : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fire-scenarios"] })
      onClose()
    },
    onError: () => setError("Failed to create scenario."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">New FIRE Scenario</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Scenario name</label>
            <input
              {...register("name")}
              placeholder="e.g. Lean FIRE, Fat FIRE"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target annual spend (today's dollars)
            </label>
            <input
              {...register("target_annual_spend")}
              placeholder="e.g. 60000"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.target_annual_spend && (
              <p className="mt-1 text-xs text-red-600">{errors.target_annual_spend.message}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Safe withdrawal rate (default 4%)
            </label>
            <input
              {...register("safe_withdrawal_rate")}
              placeholder="e.g. 0.04"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Target retirement age (optional)
            </label>
            <input
              {...register("target_retirement_age")}
              type="number"
              placeholder="e.g. 55"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
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
            {isSubmitting ? "Creating…" : "Create Scenario"}
          </button>
        </form>
      </div>
    </div>
  )
}

function ScenarioCard({ scenario }: { scenario: FireScenarioResponse }) {
  return (
    <Link
      to="/fire/$scenarioId"
      params={{ scenarioId: scenario.id }}
      className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-indigo-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">{scenario.name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Target spend: {formatCurrency(scenario.target_annual_spend)}/yr
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            SWR: {(Number(scenario.safe_withdrawal_rate) * 100).toFixed(1)}%
          </p>
        </div>
        <div className="text-right">
          {scenario.detected_portfolio_value && (
            <p className="text-sm font-medium text-indigo-600">
              Portfolio: {formatCurrency(scenario.detected_portfolio_value)}
            </p>
          )}
          {scenario.detected_at && (
            <p className="text-xs text-gray-400 mt-0.5">
              Detected {new Date(scenario.detected_at).toLocaleDateString()}
            </p>
          )}
        </div>
      </div>
    </Link>
  )
}

export default function Fire() {
  const [showNew, setShowNew] = useState(false)

  const { data: scenarios, isLoading } = useQuery({
    queryKey: ["fire-scenarios"],
    queryFn: () => fireApi.list(),
  })

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">FIRE Scenarios</h1>
          <p className="text-sm text-gray-500 mt-0.5">Model your path to financial independence</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          New Scenario
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading…</p>}

      {scenarios && scenarios.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500 mb-3">No FIRE scenarios yet.</p>
          <button
            onClick={() => setShowNew(true)}
            className="text-indigo-600 text-sm hover:underline"
          >
            Create your first scenario
          </button>
        </div>
      )}

      {scenarios && scenarios.length > 0 && (
        <div className="space-y-3">
          {scenarios.map((s) => (
            <ScenarioCard key={s.id} scenario={s} />
          ))}
        </div>
      )}

      {showNew && <NewScenarioModal onClose={() => setShowNew(false)} />}
    </div>
  )
}
