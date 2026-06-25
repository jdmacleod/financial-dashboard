import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ApiError } from "@/api/client"
import { membersApi } from "@/api/members"
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

function ProfileForm({ member }: { member: MemberResponse }) {
  const queryClient = useQueryClient()
  const [displayName, setDisplayName] = useState(member.display_name)
  const [dob, setDob] = useState(member.date_of_birth ?? "")
  const [retirementAge, setRetirementAge] = useState(member.retirement_target_age?.toString() ?? "")
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const today = new Date().toISOString().slice(0, 10)
  const dobInFuture = dob !== "" && dob > today
  const retirementAgeNum = retirementAge === "" ? null : Number(retirementAge)
  const retirementAgeInvalid =
    retirementAgeNum !== null &&
    (!Number.isInteger(retirementAgeNum) || retirementAgeNum < 18 || retirementAgeNum > 100)
  const hasChanges =
    displayName !== member.display_name ||
    dob !== (member.date_of_birth ?? "") ||
    retirementAge !== (member.retirement_target_age?.toString() ?? "")

  const update = useMutation({
    mutationFn: () => {
      const changes: {
        display_name?: string
        date_of_birth?: string | null
        retirement_target_age?: number | null
      } = {}
      if (displayName !== member.display_name) changes.display_name = displayName
      if (dob !== (member.date_of_birth ?? "")) changes.date_of_birth = dob || null
      if (retirementAge !== (member.retirement_target_age?.toString() ?? ""))
        changes.retirement_target_age = retirementAgeNum
      return membersApi.update(member.id, changes)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-member", member.id] })
      queryClient.invalidateQueries({ queryKey: ["members"] })
      setSaved(true)
      setError(null)
    },
    onError: (err: unknown) => {
      setSaved(false)
      if (err instanceof ApiError && err.status === 403) {
        setError("You don't have permission to make this change.")
      } else {
        setError("Failed to save your profile.")
      }
    },
  })

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        update.mutate()
      }}
      className="bg-white rounded-xl border border-gray-200 p-6 space-y-5"
    >
      <div>
        <label htmlFor="profile-name" className="block text-sm font-medium text-gray-700 mb-1">
          Display name
        </label>
        <input
          id="profile-name"
          value={displayName}
          onChange={(e) => {
            setDisplayName(e.target.value)
            setSaved(false)
            setError(null)
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div>
        <span className="block text-sm font-medium text-gray-700 mb-1">Role</span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[member.role]}`}
        >
          {ROLE_LABELS[member.role]}
        </span>
        <p className="mt-1 text-xs text-gray-400">Contact a primary member to change your role.</p>
      </div>

      <div>
        <label htmlFor="profile-dob" className="block text-sm font-medium text-gray-700 mb-1">
          Date of birth
        </label>
        <input
          id="profile-dob"
          type="date"
          value={dob}
          max={today}
          onChange={(e) => {
            setDob(e.target.value)
            setSaved(false)
            setError(null)
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {dobInFuture && (
          <p className="mt-1 text-xs text-red-600">Date of birth can't be in the future.</p>
        )}
      </div>

      <div>
        <label
          htmlFor="profile-retirement-age"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          Target retirement age
        </label>
        <input
          id="profile-retirement-age"
          type="number"
          min={18}
          max={100}
          step={1}
          value={retirementAge}
          placeholder="e.g. 65"
          onChange={(e) => {
            setRetirementAge(e.target.value)
            setSaved(false)
            setError(null)
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p className="mt-1 text-xs text-gray-400">
          The age you plan to retire. Adds a "Target retirement" marker to your{" "}
          <a href="/reports/milestones" className="text-indigo-600 hover:underline">
            milestone timeline
          </a>
          . Leave blank to remove it.
        </p>
        {retirementAgeInvalid && (
          <p className="mt-1 text-xs text-red-600">Enter a whole age between 18 and 100.</p>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      {saved && (
        <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
          Profile saved.
        </p>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!hasChanges || dobInFuture || retirementAgeInvalid || update.isPending}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {update.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  )
}

export default function Profile() {
  const memberId = useAuth((s) => s.memberId)

  const {
    data: member,
    isLoading,
    error: loadError,
  } = useQuery({
    queryKey: ["current-member", memberId],
    queryFn: () => membersApi.get(memberId!),
    enabled: !!memberId,
  })

  return (
    <div className="p-8 max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Your profile</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Update your own name and date of birth. Your date of birth powers age-based projections
          like FIRE, Social Security, and required minimum distributions.
        </p>
      </div>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
      {loadError && <div className="text-sm text-red-500 py-4">Failed to load your profile.</div>}

      {member && <ProfileForm key={member.id} member={member} />}
    </div>
  )
}
