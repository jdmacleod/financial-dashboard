import { useState, useMemo } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { insurancePoliciesApi } from "@/api/insurancePolicies"
import { membersApi } from "@/api/members"
import { ownershipEntitiesApi } from "@/api/ownershipEntities"
import { propertiesApi } from "@/api/properties"
import { QueryGuard } from "@/components/app/QueryGuard"
import { formatCurrency } from "@/lib/formatters"
import type { InsurancePolicyResponse } from "@/api/types"

// ── Constants ─────────────────────────────────────────────────────────────────

const POLICY_TYPES = [
  "term_life",
  "permanent_life",
  "umbrella_liability",
  "disability",
  "long_term_care",
  "scheduled_specialty",
  "homeowners",
  "renters",
] as const

type PolicyType = (typeof POLICY_TYPES)[number]

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

// Policy types for which a specific member is insured
const MEMBER_INSURED_TYPES: PolicyType[] = [
  "term_life",
  "permanent_life",
  "disability",
  "long_term_care",
]

// Policy types for which an entity can own the policy
const ENTITY_OWNER_TYPES: PolicyType[] = ["term_life", "permanent_life"]

// Policy types that can be linked to a real estate property
const PROPERTY_LINKED_TYPES: PolicyType[] = ["homeowners", "renters"]

type PolicySort = "type_asc" | "coverage_desc" | "premium_desc"

function policyTypeLabel(slug: string): string {
  return (
    POLICY_TYPE_LABELS[slug] ??
    slug
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  )
}

// ── Schemas ───────────────────────────────────────────────────────────────────

const policySchema = z.object({
  policy_type: z.enum(POLICY_TYPES),
  coverage_amount: z
    .string()
    .min(1, "Required")
    .refine((v) => Number(v) >= 0, "Must be 0 or greater"),
  premium_amount: z
    .string()
    .min(1, "Required")
    .refine((v) => Number(v) >= 0, "Must be 0 or greater"),
  premium_cadence: z.enum(["monthly", "quarterly", "annual"]),
  carrier: z.string().nullable(),
  policy_number: z.string().nullable(),
  technical_notes: z.string().nullable(),
  insured_real_estate_id: z.string().nullable(),
  insured_member_id: z.string().nullable(),
  owner_ownership_entity_id: z.string().nullable(),
})
type PolicyForm = z.infer<typeof policySchema>

// ── AddPolicyModal ────────────────────────────────────────────────────────────

function AddPolicyModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { data: members } = useQuery({ queryKey: ["members"], queryFn: membersApi.list })
  const { data: entities } = useQuery({
    queryKey: ["ownership-entities"],
    queryFn: ownershipEntitiesApi.list,
  })
  const { data: properties } = useQuery({
    queryKey: ["properties"],
    queryFn: propertiesApi.list,
  })

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PolicyForm>({
    resolver: zodResolver(policySchema),
    defaultValues: {
      policy_type: "term_life",
      premium_cadence: "annual",
      coverage_amount: "",
      premium_amount: "",
      carrier: null,
      policy_number: null,
      technical_notes: null,
      insured_real_estate_id: null,
      insured_member_id: null,
      owner_ownership_entity_id: null,
    },
  })

  const policyType = watch("policy_type")

  const create = useMutation({
    mutationFn: (data: PolicyForm) =>
      insurancePoliciesApi.create({
        policy_type: data.policy_type,
        coverage_amount: data.coverage_amount,
        premium_amount: data.premium_amount,
        premium_cadence: data.premium_cadence,
        insured_member_id: data.insured_member_id || null,
        owner_ownership_entity_id: data.owner_ownership_entity_id || null,
        cash_value_account_id: null,
        carrier: data.carrier || null,
        policy_number: data.policy_number || null,
        technical_notes: data.technical_notes || null,
        insured_real_estate_id: data.insured_real_estate_id || null,
        metadata: {},
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insurance-policies"] })
      onClose()
    },
    onError: () => setError("Failed to add policy."),
  })

  const activeMembers = members?.filter((m) => m.is_active) ?? []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Add Policy</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Policy type</label>
            <select
              {...register("policy_type")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {POLICY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {POLICY_TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Coverage amount</label>
            <input
              {...register("coverage_amount")}
              placeholder="e.g. 1000000"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.coverage_amount && (
              <p className="mt-1 text-xs text-red-600">{errors.coverage_amount.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Premium</label>
            <div className="flex gap-2">
              <input
                {...register("premium_amount")}
                placeholder="e.g. 2400"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <select
                {...register("premium_cadence")}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
              </select>
            </div>
            {errors.premium_amount && (
              <p className="mt-1 text-xs text-red-600">{errors.premium_amount.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Carrier{" "}
              <span className="text-gray-400 font-normal">(optional — e.g. USAA, Chubb)</span>
            </label>
            <input
              {...register("carrier")}
              placeholder="e.g. Northwestern Mutual"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Policy number <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              {...register("policy_number")}
              placeholder="e.g. LF-2024-00123"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Technical notes <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea
              {...register("technical_notes")}
              placeholder="e.g. Comprehensive, flood rider, earthquake endorsement"
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>

          {PROPERTY_LINKED_TYPES.includes(policyType as PolicyType) &&
            properties &&
            properties.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Covered property <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <select
                  {...register("insured_real_estate_id")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">None</option>
                  {properties.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nickname}
                    </option>
                  ))}
                </select>
              </div>
            )}

          {MEMBER_INSURED_TYPES.includes(policyType as PolicyType) && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Insured member <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <select
                {...register("insured_member_id")}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">None</option>
                {activeMembers.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {ENTITY_OWNER_TYPES.includes(policyType as PolicyType) && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Trust / entity owner{" "}
                <span className="text-gray-400 font-normal">
                  (optional — for ILIT-held policies)
                </span>
              </label>
              <select
                {...register("owner_ownership_entity_id")}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">None (personally owned)</option>
                {entities?.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name} ({e.entity_type})
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

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {isSubmitting ? "Adding…" : "Add Policy"}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── EditPolicyModal ───────────────────────────────────────────────────────────

function EditPolicyModal({
  policy,
  onClose,
}: {
  policy: InsurancePolicyResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { data: properties } = useQuery({
    queryKey: ["properties"],
    queryFn: propertiesApi.list,
  })

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<PolicyForm>({
    resolver: zodResolver(policySchema),
    defaultValues: {
      policy_type: policy.policy_type as PolicyType,
      coverage_amount: String(Number(policy.coverage_amount)),
      premium_amount: String(Number(policy.premium_amount)),
      premium_cadence: policy.premium_cadence as "monthly" | "quarterly" | "annual",
      carrier: policy.carrier,
      policy_number: policy.policy_number,
      technical_notes: policy.technical_notes,
      insured_real_estate_id: policy.insured_real_estate_id,
      insured_member_id: policy.insured_member_id,
      owner_ownership_entity_id: policy.owner_ownership_entity_id,
    },
  })

  const policyType = watch("policy_type")

  const update = useMutation({
    mutationFn: (data: PolicyForm) =>
      insurancePoliciesApi.update(policy.id, {
        policy_type: data.policy_type,
        coverage_amount: data.coverage_amount,
        premium_amount: data.premium_amount,
        premium_cadence: data.premium_cadence,
        carrier: data.carrier || null,
        policy_number: data.policy_number || null,
        technical_notes: data.technical_notes || null,
        insured_real_estate_id: data.insured_real_estate_id || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insurance-policies"] })
      onClose()
    },
    onError: () => setError("Failed to save changes."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-semibold">Edit Policy</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{policyTypeLabel(policy.policy_type)}</p>
        <form onSubmit={handleSubmit((d) => update.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Policy type</label>
            <select
              {...register("policy_type")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {POLICY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {POLICY_TYPE_LABELS[t]}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Coverage amount</label>
            <input
              {...register("coverage_amount")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.coverage_amount && (
              <p className="mt-1 text-xs text-red-600">{errors.coverage_amount.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Premium</label>
            <div className="flex gap-2">
              <input
                {...register("premium_amount")}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <select
                {...register("premium_cadence")}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
              </select>
            </div>
            {errors.premium_amount && (
              <p className="mt-1 text-xs text-red-600">{errors.premium_amount.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Carrier <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              {...register("carrier")}
              placeholder="e.g. Northwestern Mutual"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Policy number <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              {...register("policy_number")}
              placeholder="e.g. LF-2024-00123"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Technical notes <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea
              {...register("technical_notes")}
              placeholder="e.g. Comprehensive, flood rider, earthquake endorsement"
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>

          {PROPERTY_LINKED_TYPES.includes(policyType as PolicyType) &&
            properties &&
            properties.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Covered property <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <select
                  {...register("insured_real_estate_id")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">None</option>
                  {properties.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nickname}
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

// ── PolicyCard ────────────────────────────────────────────────────────────────

function PolicyCard({
  policy,
  memberName,
  entityName,
  entityCountsInNW,
  propertyNickname,
  onDelete,
}: {
  policy: InsurancePolicyResponse
  memberName: string | null
  entityName: string | null
  entityCountsInNW: boolean | null
  propertyNickname: string | null
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)

  return (
    <>
      <div
        className="rounded-lg border p-4"
        style={{ borderColor: "var(--bd)", background: "var(--card)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {policyTypeLabel(policy.policy_type)}
              </span>
              <span className="text-sm flex-shrink-0 ml-3" style={{ color: "var(--label)" }}>
                {formatCurrency(policy.premium_amount)}
                {CADENCE_LABELS[policy.premium_cadence] ?? ""}
              </span>
            </div>
            <div className="mt-0.5 text-sm" style={{ color: "var(--label)" }}>
              {formatCurrency(policy.coverage_amount)} coverage
            </div>
            {policy.carrier && (
              <div className="mt-1 text-xs" style={{ color: "var(--label)" }}>
                {policy.carrier}
                {policy.policy_number && (
                  <span className="ml-2 font-mono opacity-75">#{policy.policy_number}</span>
                )}
              </div>
            )}
            {propertyNickname && (
              <div className="mt-1 text-xs" style={{ color: "var(--label)" }}>
                Property: {propertyNickname}
              </div>
            )}
            {memberName && (
              <div className="mt-1 text-xs" style={{ color: "var(--label)" }}>
                Insured: {memberName}
              </div>
            )}
            {policy.technical_notes && (
              <div className="mt-1 text-xs italic" style={{ color: "var(--label)", opacity: 0.85 }}>
                {policy.technical_notes}
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-2">
              {entityName && (
                <span
                  className="rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
                >
                  {entityCountsInNW === false ? `${entityName} (outside estate)` : entityName}
                </span>
              )}
              {policy.cash_value_account_id && (
                <span
                  className="rounded-full px-2 py-0.5 text-xs font-medium"
                  style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
                >
                  Cash value in net worth
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 pt-0.5">
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
      </div>
      {editing && <EditPolicyModal policy={policy} onClose={() => setEditing(false)} />}
    </>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Insurance() {
  const queryClient = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [sort, setSort] = useState<PolicySort>("type_asc")

  const query = useQuery({
    queryKey: ["insurance-policies"],
    queryFn: () => insurancePoliciesApi.list(),
  })

  const { data: members } = useQuery({ queryKey: ["members"], queryFn: membersApi.list })
  const { data: entities } = useQuery({
    queryKey: ["ownership-entities"],
    queryFn: ownershipEntitiesApi.list,
  })
  const { data: properties } = useQuery({
    queryKey: ["properties"],
    queryFn: propertiesApi.list,
  })

  const memberMap = useMemo(() => new Map(members?.map((m) => [m.id, m]) ?? []), [members])
  const entityMap = useMemo(() => new Map(entities?.map((e) => [e.id, e]) ?? []), [entities])
  const propertyMap = useMemo(() => new Map(properties?.map((p) => [p.id, p]) ?? []), [properties])

  const remove = useMutation({
    mutationFn: (id: string) => insurancePoliciesApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["insurance-policies"] }),
  })

  const sortedPolicies = useMemo(() => {
    if (!query.data) return []
    return [...query.data].sort((a, b) => {
      if (sort === "type_asc")
        return policyTypeLabel(a.policy_type).localeCompare(policyTypeLabel(b.policy_type))
      if (sort === "coverage_desc") return Number(b.coverage_amount) - Number(a.coverage_amount)
      if (sort === "premium_desc") return Number(b.premium_amount) - Number(a.premium_amount)
      return 0
    })
  }, [query.data, sort])

  return (
    <div className="mx-auto max-w-3xl p-4">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-xl font-semibold" style={{ color: "var(--text)" }}>
          Insurance
        </h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Add policy
        </button>
      </div>
      <p className="mb-6 text-sm" style={{ color: "var(--label)" }}>
        Coverage carried across the household, including policies held in trust.
      </p>

      <QueryGuard
        query={query}
        empty={
          <div
            className="rounded-lg border border-dashed p-8 text-center text-sm"
            style={{ color: "var(--label)" }}
          >
            <p className="mb-3">No insurance policies yet.</p>
            <button
              onClick={() => setShowAdd(true)}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Add first policy
            </button>
          </div>
        }
      >
        {() => (
          <div>
            {sortedPolicies.length > 0 && (
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-gray-500">
                  {sortedPolicies.length} {sortedPolicies.length === 1 ? "policy" : "policies"}
                </span>
                <select
                  aria-label="Sort policies"
                  value={sort}
                  onChange={(e) => setSort(e.target.value as PolicySort)}
                  className="text-xs text-gray-500 border-0 bg-transparent cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
                >
                  <option value="type_asc">Type A–Z</option>
                  <option value="coverage_desc">Coverage ↓</option>
                  <option value="premium_desc">Premium ↓</option>
                </select>
              </div>
            )}
            <div className="space-y-3">
              {sortedPolicies.map((p) => {
                const member = p.insured_member_id ? memberMap.get(p.insured_member_id) : null
                const entity = p.owner_ownership_entity_id
                  ? entityMap.get(p.owner_ownership_entity_id)
                  : null
                const property = p.insured_real_estate_id
                  ? propertyMap.get(p.insured_real_estate_id)
                  : null
                return (
                  <PolicyCard
                    key={p.id}
                    policy={p}
                    memberName={member?.display_name ?? null}
                    entityName={entity?.name ?? null}
                    entityCountsInNW={entity?.counts_in_personal_net_worth ?? null}
                    propertyNickname={property?.nickname ?? null}
                    onDelete={() => {
                      if (window.confirm("Delete this insurance policy?")) remove.mutate(p.id)
                    }}
                  />
                )
              })}
            </div>
          </div>
        )}
      </QueryGuard>

      {showAdd && <AddPolicyModal onClose={() => setShowAdd(false)} />}
    </div>
  )
}
