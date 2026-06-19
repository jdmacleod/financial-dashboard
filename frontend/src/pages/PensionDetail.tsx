import { useState } from "react"
import { useParams, Link } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { pensionApi } from "@/api/pension"
import { accountsApi } from "@/api/accounts"
import { membersApi } from "@/api/members"
import { formatCurrency } from "@/lib/formatters"
import type { PensionAccountCreate, PensionAccountUpdate } from "@/api/types"

const pensionSchema = z.object({
  member_id: z.string().optional().nullable(),
  plan_name: z.string().optional().nullable(),
  administrator: z.string().optional().nullable(),
  monthly_benefit_estimate: z.string().optional().nullable(),
  eligibility_age: z.coerce.number().int().min(50).max(90).optional().nullable(),
  eligibility_date: z.string().optional().nullable(),
  cola_adjustment_rate: z.string().optional().nullable(),
  is_vested: z.boolean().optional(),
  vesting_date: z.string().optional().nullable(),
  survivor_benefit_percent: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
})
type PensionForm = z.infer<typeof pensionSchema>

function formatPercent(val: string | null | undefined): string {
  if (!val) return "—"
  return `${(Number(val) * 100).toFixed(1)}%`
}

export default function PensionDetail() {
  const { accountId } = useParams({ strict: false }) as { accountId: string }
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const { data: account } = useQuery({
    queryKey: ["account", accountId],
    queryFn: () => accountsApi.get(accountId),
  })

  const { data: pension, isLoading } = useQuery({
    queryKey: ["pension", accountId],
    queryFn: () => pensionApi.get(accountId),
    retry: false,
  })

  const { data: members } = useQuery({
    queryKey: ["members"],
    queryFn: membersApi.list,
  })

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PensionForm>({
    resolver: zodResolver(pensionSchema),
    defaultValues: pension
      ? {
          member_id: pension.member_id,
          plan_name: pension.plan_name,
          administrator: pension.administrator,
          monthly_benefit_estimate: pension.monthly_benefit_estimate,
          eligibility_age: pension.eligibility_age,
          eligibility_date: pension.eligibility_date,
          cola_adjustment_rate: String(Number(pension.cola_adjustment_rate) * 100),
          is_vested: pension.is_vested,
          vesting_date: pension.vesting_date,
          survivor_benefit_percent: pension.survivor_benefit_percent
            ? String(Number(pension.survivor_benefit_percent) * 100)
            : null,
          notes: pension.notes,
        }
      : {},
  })

  const isVested = watch("is_vested")

  const createMutation = useMutation({
    mutationFn: (data: PensionAccountCreate) => pensionApi.create(accountId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pension", accountId] })
      setEditing(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
    onError: () => setSaveError("Failed to save pension record."),
  })

  const updateMutation = useMutation({
    mutationFn: (data: PensionAccountUpdate) => pensionApi.update(accountId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pension", accountId] })
      setEditing(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
    onError: () => setSaveError("Failed to save pension record."),
  })

  function handleSave(formData: PensionForm) {
    setSaveError(null)
    const colaRate = formData.cola_adjustment_rate
      ? String(Number(formData.cola_adjustment_rate) / 100)
      : "0.02"
    const survivorPct = formData.survivor_benefit_percent
      ? String(Number(formData.survivor_benefit_percent) / 100)
      : null

    const payload = {
      member_id: formData.member_id || null,
      plan_name: formData.plan_name || null,
      administrator: formData.administrator || null,
      monthly_benefit_estimate: formData.monthly_benefit_estimate || null,
      eligibility_age: formData.eligibility_age ?? null,
      eligibility_date: formData.eligibility_date || null,
      cola_adjustment_rate: colaRate,
      is_vested: formData.is_vested ?? false,
      vesting_date: formData.vesting_date || null,
      survivor_benefit_percent: survivorPct,
      notes: formData.notes || null,
    }

    if (pension) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  function startEdit() {
    if (pension) {
      reset({
        member_id: pension.member_id,
        plan_name: pension.plan_name,
        administrator: pension.administrator,
        monthly_benefit_estimate: pension.monthly_benefit_estimate,
        eligibility_age: pension.eligibility_age,
        eligibility_date: pension.eligibility_date,
        cola_adjustment_rate: pension.cola_adjustment_rate
          ? String(Number(pension.cola_adjustment_rate) * 100)
          : "2",
        is_vested: pension.is_vested,
        vesting_date: pension.vesting_date,
        survivor_benefit_percent: pension.survivor_benefit_percent
          ? String(Number(pension.survivor_benefit_percent) * 100)
          : null,
        notes: pension.notes,
      })
    }
    setEditing(true)
  }

  if (isLoading) {
    return (
      <div className="p-8 max-w-2xl mx-auto space-y-4">
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse" />
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link
          to="/accounts/$accountId/transactions"
          params={{ accountId }}
          className="text-sm text-indigo-600 hover:underline"
        >
          &larr; {account?.nickname ?? "Account"}
        </Link>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pension Details</h1>
        {!editing && (
          <button
            onClick={startEdit}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {pension ? "Edit" : "Set up pension"}
          </button>
        )}
      </div>

      {saved && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
          Pension details saved.
        </div>
      )}

      {!editing && pension && (
        <div className="space-y-4">
          {/* Plan Identity */}
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Plan Identity</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-500">Plan name</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{pension.plan_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Administrator</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{pension.administrator ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Member</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {members?.find((m) => m.id === pension.member_id)?.display_name ?? "—"}
                </dd>
              </div>
            </dl>
          </section>

          {/* Benefit Details */}
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Benefit Details</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-500">Monthly benefit estimate</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {pension.monthly_benefit_estimate
                    ? formatCurrency(pension.monthly_benefit_estimate)
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Annual equivalent</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {pension.monthly_benefit_estimate
                    ? formatCurrency(String(Number(pension.monthly_benefit_estimate) * 12))
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Eligibility age</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {pension.eligibility_age ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Eligibility date</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {pension.eligibility_date ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">COLA adjustment</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {formatPercent(pension.cola_adjustment_rate)} / yr
                </dd>
              </div>
            </dl>
          </section>

          {/* Vesting & Survivor */}
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Vesting &amp; Survivor</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-500">Vested</dt>
                <dd className="mt-0.5">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      pension.is_vested
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {pension.is_vested ? "Yes" : "Not yet"}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Vesting date</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{pension.vesting_date ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Survivor benefit</dt>
                <dd className="font-medium text-gray-900 mt-0.5">
                  {formatPercent(pension.survivor_benefit_percent)}
                </dd>
              </div>
            </dl>
          </section>

          {pension.is_vested && pension.monthly_benefit_estimate && (
            <div className="rounded-lg bg-indigo-50 border border-indigo-200 px-4 py-3 text-sm text-indigo-800">
              This pension is vested and will appear as an auto-detected income stream in your FIRE
              scenarios.
            </div>
          )}

          {pension.notes && (
            <section className="bg-white rounded-xl border border-gray-200 p-5">
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Notes</h2>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{pension.notes}</p>
            </section>
          )}
        </div>
      )}

      {!editing && !pension && (
        <div className="text-center py-16 text-gray-400 border border-dashed border-gray-200 rounded-xl">
          <p className="text-base mb-2">No pension record yet</p>
          <p className="text-sm">Set up pension details to enable FIRE income stream detection.</p>
        </div>
      )}

      {editing && (
        <form onSubmit={handleSubmit(handleSave)} className="space-y-4">
          {/* Plan Identity */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700">Plan Identity</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Plan name</label>
              <input
                {...register("plan_name")}
                placeholder="e.g. PERS, CalSTRS"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Administrator</label>
              <input
                {...register("administrator")}
                placeholder="e.g. State Board of Administration"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Member</label>
              <select
                {...register("member_id")}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">— none —</option>
                {members?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* Benefit Details */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700">Benefit Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Monthly benefit estimate
                </label>
                <input
                  {...register("monthly_benefit_estimate")}
                  placeholder="e.g. 2500.00"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                {errors.monthly_benefit_estimate && (
                  <p className="mt-1 text-xs text-red-600">
                    {errors.monthly_benefit_estimate.message}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  COLA rate (%)
                </label>
                <input
                  {...register("cola_adjustment_rate")}
                  placeholder="2.0"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Eligibility age
                </label>
                <input
                  type="number"
                  {...register("eligibility_age")}
                  placeholder="65"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                {errors.eligibility_age && (
                  <p className="mt-1 text-xs text-red-600">{errors.eligibility_age.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Eligibility date
                </label>
                <input
                  type="date"
                  {...register("eligibility_date")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          </section>

          {/* Vesting & Survivor */}
          <section className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <h2 className="text-sm font-semibold text-gray-700">Vesting &amp; Survivor</h2>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="is_vested"
                {...register("is_vested")}
                className="h-4 w-4 rounded border-gray-300 text-indigo-600"
              />
              <label htmlFor="is_vested" className="text-sm font-medium text-gray-700">
                Vested
              </label>
            </div>
            {isVested && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Vesting date</label>
                <input
                  type="date"
                  {...register("vesting_date")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Survivor benefit (%)
              </label>
              <input
                {...register("survivor_benefit_percent")}
                placeholder="e.g. 50"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </section>

          {/* Notes */}
          <section className="bg-white rounded-xl border border-gray-200 p-5">
            <label className="block text-sm font-semibold text-gray-700 mb-2">Notes</label>
            <textarea
              {...register("notes")}
              rows={3}
              placeholder="Optional notes about this pension plan"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none"
            />
          </section>

          {saveError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {saveError}
            </p>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => {
                setEditing(false)
                setSaveError(null)
              }}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {isSubmitting || createMutation.isPending || updateMutation.isPending
                ? "Saving…"
                : "Save"}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
