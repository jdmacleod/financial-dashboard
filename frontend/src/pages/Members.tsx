import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ApiError } from "@/api/client"
import { membersApi } from "@/api/members"
import { AddPersonSlideOver } from "@/components/app/AddPersonSlideOver"
import { useAuth } from "@/hooks/useAuth"
import type { MemberResponse } from "@/api/types"

const ROLE_LABELS: Record<string, string> = {
  primary: "Primary",
  partner: "Partner",
  dependent: "Dependent",
}

const ROLE_COLORS: Record<string, string> = {
  primary: "bg-indigo-100 text-indigo-700",
  partner: "bg-emerald-100 text-emerald-700",
  dependent: "bg-gray-100 text-gray-600",
}

function MemberSlideOver({ member, onClose }: { member: MemberResponse; onClose: () => void }) {
  const queryClient = useQueryClient()
  const viewerIsPrimary = useAuth((s) => s.role === "primary")
  const [displayName, setDisplayName] = useState(member.display_name)
  const [role, setRole] = useState<"primary" | "partner" | "dependent">(member.role)
  const [dob, setDob] = useState(member.date_of_birth ?? "")
  const [retirementAge, setRetirementAge] = useState(member.retirement_target_age?.toString() ?? "")
  const [confirmPromotion, setConfirmPromotion] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const today = new Date().toISOString().slice(0, 10)
  const dobInFuture = dob !== "" && dob > today
  const retirementAgeNum = retirementAge === "" ? null : Number(retirementAge)
  const retirementAgeInvalid =
    retirementAgeNum !== null &&
    (!Number.isInteger(retirementAgeNum) || retirementAgeNum < 18 || retirementAgeNum > 100)
  const hasChanges =
    displayName !== member.display_name ||
    role !== member.role ||
    dob !== (member.date_of_birth ?? "") ||
    retirementAge !== (member.retirement_target_age?.toString() ?? "")

  const update = useMutation({
    mutationFn: () => {
      const changes: {
        display_name?: string
        role?: "primary" | "partner" | "dependent"
        date_of_birth?: string | null
        retirement_target_age?: number | null
      } = {}
      if (displayName !== member.display_name) changes.display_name = displayName
      if (role !== member.role) changes.role = role
      if (dob !== (member.date_of_birth ?? "")) changes.date_of_birth = dob || null
      if (retirementAge !== (member.retirement_target_age?.toString() ?? ""))
        changes.retirement_target_age = retirementAgeNum
      return membersApi.update(member.id, changes)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] })
      onClose()
    },
    onError: (err: unknown) => {
      setConfirmPromotion(false)
      if (err instanceof ApiError && err.status === 409) {
        setError("Cannot change role — at least one primary member must remain.")
      } else {
        setError("Failed to update member.")
      }
    },
  })

  function handleSave() {
    if (role === "primary" && role !== member.role && !confirmPromotion) {
      setConfirmPromotion(true)
      return
    }
    update.mutate()
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-sm bg-white shadow-xl p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Edit member</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Display name</label>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div>
          <span className="block text-sm font-medium text-gray-700 mb-1">Role</span>
          {viewerIsPrimary ? (
            <select
              value={role}
              onChange={(e) => {
                setRole(e.target.value as typeof role)
                setConfirmPromotion(false)
                setError(null)
              }}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="primary">Primary</option>
              <option value="partner">Partner</option>
              <option value="dependent">Dependent</option>
            </select>
          ) : (
            <>
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[member.role]}`}
              >
                {ROLE_LABELS[member.role]}
              </span>
              <p className="mt-1 text-xs text-gray-400">
                Contact a primary member to change roles.
              </p>
            </>
          )}
        </div>

        <div>
          <label htmlFor="member-dob" className="block text-sm font-medium text-gray-700 mb-1">
            Date of birth
          </label>
          <input
            id="member-dob"
            type="date"
            value={dob}
            max={today}
            onChange={(e) => {
              setDob(e.target.value)
              setError(null)
            }}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-400">
            Used for age-based projections like FIRE and required minimum distributions.
          </p>
          {dobInFuture && (
            <p className="mt-1 text-xs text-red-600">Date of birth can't be in the future.</p>
          )}
        </div>

        <div>
          <label
            htmlFor="member-retirement-age"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Target retirement age
          </label>
          <input
            id="member-retirement-age"
            type="number"
            min={18}
            max={100}
            step={1}
            value={retirementAge}
            placeholder="e.g. 65"
            onChange={(e) => {
              setRetirementAge(e.target.value)
              setError(null)
            }}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <p className="mt-1 text-xs text-gray-400">
            Optional. Adds a "Target retirement" marker to the milestone timeline. Leave blank to
            remove it.
          </p>
          {retirementAgeInvalid && (
            <p className="mt-1 text-xs text-red-600">Enter a whole age between 18 and 100.</p>
          )}
        </div>

        {confirmPromotion && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
            <p className="font-medium mb-1">Grant primary access?</p>
            <p className="text-xs">
              {member.display_name} will gain full admin access — backups, exports, and member
              management. Click Save to confirm.
            </p>
          </div>
        )}

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex gap-3 mt-auto">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={update.isPending || !hasChanges || dobInFuture || retirementAgeInvalid}
            className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {update.isPending ? "Saving…" : confirmPromotion ? "Confirm & Save" : "Save"}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Members() {
  const canInvite = useAuth((s) => s.role === "primary" || s.role === "partner")
  const {
    data: members,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["members"],
    queryFn: membersApi.list,
  })
  const [selected, setSelected] = useState<MemberResponse | null>(null)
  const [showAdd, setShowAdd] = useState(false)

  if (isLoading) return <div className="p-8 text-gray-500">Loading members…</div>
  if (error) return <div className="p-8 text-red-600">Failed to load members.</div>

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Members</h1>
        {canInvite && (
          <button
            onClick={() => setShowAdd(true)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            Add person
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {members?.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelected(m)}
            className="w-full flex items-center gap-4 px-4 py-3 hover:bg-gray-50 text-left transition-colors"
          >
            <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-sm shrink-0">
              {m.display_name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 truncate">{m.display_name}</p>
              <p className="text-sm text-gray-500">{m.is_active ? "Active" : "Inactive"}</p>
            </div>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[m.role]}`}
            >
              {ROLE_LABELS[m.role]}
            </span>
          </button>
        ))}
        {members?.length === 0 && (
          <p className="px-4 py-8 text-center text-gray-400">No members yet.</p>
        )}
      </div>

      {selected && <MemberSlideOver member={selected} onClose={() => setSelected(null)} />}
      {showAdd && <AddPersonSlideOver onClose={() => setShowAdd(false)} />}
    </div>
  )
}
