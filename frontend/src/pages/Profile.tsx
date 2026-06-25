import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ApiError } from "@/api/client"
import { membersApi } from "@/api/members"
import { useAuth } from "@/hooks/useAuth"
import { formatCurrency } from "@/lib/formatters"
import type { MemberResponse } from "@/api/types"

function fraLabel(months: number): string {
  const y = Math.floor(months / 12)
  const m = months % 12
  return m === 0 ? `${y}` : `${y} yr ${m} mo`
}

const CLAIM_AGES = [62, 63, 64, 65, 66, 67, 68, 69, 70]

function SocialSecurityEstimator({ member }: { member: MemberResponse }) {
  const queryClient = useQueryClient()
  const [benefit, setBenefit] = useState(member.ss_monthly_benefit_at_fra ?? "")
  const [claimAge, setClaimAge] = useState(member.ss_claiming_age?.toString() ?? "")
  const [saved, setSaved] = useState(false)
  const valid = benefit !== "" && Number(benefit) > 0

  const { data, isFetching } = useQuery({
    queryKey: ["ss-estimate", member.id, benefit],
    queryFn: () => membersApi.socialSecurityEstimate(member.id, benefit),
    enabled: valid && !!member.date_of_birth,
  })

  const hasChanges =
    benefit !== (member.ss_monthly_benefit_at_fra ?? "") ||
    claimAge !== (member.ss_claiming_age?.toString() ?? "")

  const save = useMutation({
    mutationFn: () =>
      membersApi.update(member.id, {
        ss_monthly_benefit_at_fra: benefit || null,
        ss_claiming_age: claimAge ? Number(claimAge) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-member", member.id] })
      queryClient.invalidateQueries({ queryKey: ["members"] })
      setSaved(true)
    },
  })

  if (!member.date_of_birth) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-1">Social Security claiming</h2>
        <p className="text-sm text-gray-400">
          Add your date of birth above to estimate benefits by claiming age.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-900">Social Security claiming</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Enter your estimated monthly benefit at Full Retirement Age (from your SSA statement) and
          the age you plan to claim. Saved values feed your FIRE projections.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="ss-pia" className="block text-sm font-medium text-gray-700 mb-1">
            Monthly benefit at FRA
          </label>
          <input
            id="ss-pia"
            inputMode="decimal"
            value={benefit}
            placeholder="e.g. 2000"
            onChange={(e) => {
              setBenefit(e.target.value)
              setSaved(false)
            }}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label htmlFor="ss-claim-age" className="block text-sm font-medium text-gray-700 mb-1">
            Planned claiming age
          </label>
          <select
            id="ss-claim-age"
            value={claimAge}
            onChange={(e) => {
              setClaimAge(e.target.value)
              setSaved(false)
            }}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Not set</option>
            {CLAIM_AGES.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={!hasChanges || save.isPending}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {save.isPending ? "Saving…" : "Save"}
        </button>
        {saved && !hasChanges && <span className="text-sm text-emerald-700">Saved.</span>}
      </div>

      {valid && data && (
        <div>
          <p className="text-xs text-gray-400 mb-2">
            Full Retirement Age: {fraLabel(data.fra_months)}
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-400 text-left">
                <th className="py-1 font-medium">Claim age</th>
                <th className="py-1 font-medium text-right">Monthly</th>
                <th className="py-1 font-medium text-right">Annual</th>
                <th className="py-1 font-medium text-right">% of FRA</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.options.map((o) => {
                const selected = claimAge !== "" && Number(claimAge) === o.claiming_age
                return (
                  <tr
                    key={o.claiming_age}
                    className={
                      selected ? "font-semibold text-indigo-700" : o.is_fra ? "text-indigo-600" : ""
                    }
                  >
                    <td className="py-1.5">
                      {o.claiming_age}
                      {o.is_fra && <span className="ml-1 text-xs text-indigo-500">FRA</span>}
                      {selected && <span className="ml-1 text-xs text-indigo-500">your plan</span>}
                    </td>
                    <td className="py-1.5 text-right">{formatCurrency(o.monthly_benefit)}</td>
                    <td className="py-1.5 text-right text-gray-500">
                      {formatCurrency(o.annual_benefit)}
                    </td>
                    <td className="py-1.5 text-right text-gray-500">{o.pct_of_pia.toFixed(0)}%</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {valid && isFetching && !data && <p className="text-xs text-gray-400">Calculating…</p>}
    </div>
  )
}

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
      {member && <SocialSecurityEstimator key={`ss-${member.id}`} member={member} />}
    </div>
  )
}
