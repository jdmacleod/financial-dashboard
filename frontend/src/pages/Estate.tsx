import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { ownershipEntitiesApi } from "@/api/ownershipEntities"
import { membersApi } from "@/api/members"
import { AdvisoryNotesPanel } from "@/components/app/AdvisoryNotesPanel"
import { QueryGuard } from "@/components/app/QueryGuard"
import type { OwnershipEntityResponse } from "@/api/types"

const ENTITY_TYPE_OPTIONS = [
  { value: "revocable_trust", label: "Revocable Trust" },
  { value: "irrevocable_trust", label: "Irrevocable Trust" },
  { value: "ilit", label: "ILIT" },
  { value: "crt_crat", label: "Charitable Remainder Annuity Trust" },
  { value: "crt_crut", label: "Charitable Remainder Unitrust" },
  { value: "clt", label: "Charitable Lead Trust" },
  { value: "llc", label: "LLC" },
  { value: "custodial_utma", label: "UTMA Custodial" },
  { value: "custodial_ugma", label: "UGMA Custodial" },
] as const

function entityTypeLabel(slug: string): string {
  return ENTITY_TYPE_OPTIONS.find((o) => o.value === slug)?.label ?? slug
}

const entitySchema = z.object({
  entity_type: z.string().min(1, "Required"),
  name: z.string().min(1, "Required").max(200),
  grantor_member_id: z.string().nullable(),
  is_in_taxable_estate: z.boolean(),
  counts_in_personal_net_worth: z.boolean(),
})
type EntityForm = z.infer<typeof entitySchema>

function Badge({ on, onText, offText }: { on: boolean; onText: string; offText: string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        background: on ? "var(--nav-active-bg)" : "transparent",
        border: on ? "none" : "1px solid var(--bd)",
        color: on ? "var(--text)" : "var(--faint)",
      }}
    >
      {on ? onText : offText}
    </span>
  )
}

function EntityFormModal({
  editing,
  onClose,
}: {
  editing: OwnershipEntityResponse | null
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const { data: members } = useQuery({ queryKey: ["members"], queryFn: membersApi.list })

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EntityForm>({
    resolver: zodResolver(entitySchema),
    defaultValues: editing
      ? {
          entity_type: editing.entity_type,
          name: editing.name,
          grantor_member_id: editing.grantor_member_id,
          is_in_taxable_estate: editing.is_in_taxable_estate,
          counts_in_personal_net_worth: editing.counts_in_personal_net_worth,
        }
      : {
          entity_type: "revocable_trust",
          name: "",
          grantor_member_id: null,
          is_in_taxable_estate: true,
          counts_in_personal_net_worth: true,
        },
  })

  const save = useMutation({
    mutationFn: (data: EntityForm) => {
      const payload = {
        ...data,
        grantor_member_id: data.grantor_member_id || null,
      }
      return editing
        ? ownershipEntitiesApi.update(editing.id, payload)
        : ownershipEntitiesApi.create({
            entity_type: payload.entity_type,
            name: payload.name,
            grantor_member_id: payload.grantor_member_id,
            is_in_taxable_estate: payload.is_in_taxable_estate,
            counts_in_personal_net_worth: payload.counts_in_personal_net_worth,
          })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ownership-entities"] })
      onClose()
    },
    onError: () => setError("Failed to save. Please try again."),
  })

  const inputCls =
    "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            {editing ? "Edit entity" : "Add trust or entity"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit((d) => save.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select {...register("entity_type")} className={inputCls}>
              {ENTITY_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {errors.entity_type && (
              <p className="mt-1 text-xs text-red-600">{errors.entity_type.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              {...register("name")}
              placeholder="e.g. Smith Family Trust"
              className={inputCls}
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Grantor <span className="text-gray-400">(optional)</span>
            </label>
            <select {...register("grantor_member_id")} className={inputCls}>
              <option value="">None</option>
              {members?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.display_name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                {...register("counts_in_personal_net_worth")}
                className="rounded"
              />
              Count in personal net worth
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" {...register("is_in_taxable_estate")} className="rounded" />
              In taxable estate
            </label>
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {isSubmitting ? "Saving…" : editing ? "Save changes" : "Add entity"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Estate() {
  const queryClient = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [editing, setEditing] = useState<OwnershipEntityResponse | null>(null)

  const query = useQuery({
    queryKey: ["ownership-entities"],
    queryFn: () => ownershipEntitiesApi.list(),
  })

  const remove = useMutation({
    mutationFn: (id: string) => ownershipEntitiesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ownership-entities"] })
    },
  })

  function handleDelete(entity: OwnershipEntityResponse) {
    if (
      window.confirm(
        `Delete "${entity.name}"? Any accounts or properties titled to this entity will lose the trust link.`,
      )
    ) {
      remove.mutate(entity.id)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-4">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-xl font-semibold" style={{ color: "var(--text)" }}>
          Estate &amp; structure
        </h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Add entity
        </button>
      </div>
      <p className="mb-6 text-sm" style={{ color: "var(--label)" }}>
        Trusts and titling entities, and how each one affects your net worth and taxable estate.
      </p>

      <QueryGuard
        query={query}
        empty={
          <div
            className="rounded-lg border border-dashed p-8 text-center text-sm"
            style={{ color: "var(--label)" }}
          >
            No trusts or titling entities yet.{" "}
            <button onClick={() => setShowAdd(true)} className="underline hover:no-underline">
              Add one
            </button>
          </div>
        }
      >
        {(entities) => (
          <div className="space-y-4">
            {entities.map((entity) => (
              <div key={entity.id} className="space-y-3">
                <div
                  className="rounded-lg border p-4"
                  style={{ borderColor: "var(--bd)", background: "var(--card)" }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        {entity.name}
                      </div>
                      <div className="mt-0.5 text-xs" style={{ color: "var(--faint)" }}>
                        {entityTypeLabel(entity.entity_type)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => setEditing(entity)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(entity)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge
                      on={entity.counts_in_personal_net_worth}
                      onText="In net worth"
                      offText="Excluded from net worth"
                    />
                    <Badge
                      on={entity.is_in_taxable_estate}
                      onText="In taxable estate"
                      offText="Outside taxable estate"
                    />
                  </div>
                </div>
                <AdvisoryNotesPanel ownershipEntityId={entity.id} />
              </div>
            ))}
          </div>
        )}
      </QueryGuard>

      {(showAdd || editing) && (
        <EntityFormModal
          editing={editing}
          onClose={() => {
            setShowAdd(false)
            setEditing(null)
          }}
        />
      )}
    </div>
  )
}
