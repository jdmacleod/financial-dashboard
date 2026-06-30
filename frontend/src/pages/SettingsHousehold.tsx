import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ApiError } from "@/api/client"
import { householdApi } from "@/api/household"
import { useAuth } from "@/hooks/useAuth"
import type { FilingStatus, HouseholdResponse } from "@/api/types"

const FILING_STATUS_OPTIONS: { value: FilingStatus; label: string }[] = [
  { value: "single", label: "Single" },
  { value: "married_filing_jointly", label: "Married filing jointly" },
  { value: "married_filing_separately", label: "Married filing separately" },
  { value: "head_of_household", label: "Head of household" },
  { value: "qualifying_surviving_spouse", label: "Qualifying surviving spouse" },
]

// 50 states + DC, USPS codes.
const US_STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
  "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
  "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
  "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
  "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
] // prettier-ignore

function HouseholdTaxForm({ household }: { household: HouseholdResponse }) {
  const queryClient = useQueryClient()
  const [filingStatus, setFilingStatus] = useState<string>(household.filing_status ?? "")
  const [state, setState] = useState<string>(household.state ?? "")
  const [salt, setSalt] = useState<string>(household.amt_salt_preference ?? "")
  const [iso, setIso] = useState<string>(household.amt_iso_preference ?? "")
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const hasChanges =
    filingStatus !== (household.filing_status ?? "") ||
    state !== (household.state ?? "") ||
    salt !== (household.amt_salt_preference ?? "") ||
    iso !== (household.amt_iso_preference ?? "")

  const update = useMutation({
    mutationFn: () =>
      householdApi.update({
        filing_status: (filingStatus || null) as FilingStatus | null,
        state: state || null,
        amt_salt_preference: salt.trim() === "" ? null : salt,
        amt_iso_preference: iso.trim() === "" ? null : iso,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["household"] })
      setSaved(true)
      setError(null)
    },
    onError: (err: unknown) => {
      setSaved(false)
      if (err instanceof ApiError && err.status === 403) {
        setError("You don't have permission to make this change.")
      } else {
        setError("Failed to save household tax settings.")
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
        <label htmlFor="filing-status" className="block text-sm font-medium text-gray-700 mb-1">
          Filing status
        </label>
        <select
          id="filing-status"
          value={filingStatus}
          onChange={(e) => {
            setFilingStatus(e.target.value)
            setSaved(false)
            setError(null)
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Not set</option>
          {FILING_STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="state" className="block text-sm font-medium text-gray-700 mb-1">
          State of residence
        </label>
        <select
          id="state"
          value={state}
          onChange={(e) => {
            setState(e.target.value)
            setSaved(false)
            setError(null)
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Not set</option>
          {US_STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-400">
          Drives the federal and state income-tax estimates on the Cash Flow report.
        </p>
      </div>

      <div>
        <label htmlFor="amt-salt" className="block text-sm font-medium text-gray-700 mb-1">
          AMT: state/local tax add-back (annual)
        </label>
        <input
          id="amt-salt"
          type="number"
          min="0"
          step="1000"
          inputMode="decimal"
          value={salt}
          onChange={(e) => {
            setSalt(e.target.value)
            setSaved(false)
            setError(null)
          }}
          placeholder="0"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p className="mt-1 text-xs text-gray-400">
          State and local taxes you deduct, which the AMT adds back. Only relevant if you itemize;
          the estimate otherwise uses the standard deduction, so treat this as a planning input.
        </p>
      </div>

      <div>
        <label htmlFor="amt-iso" className="block text-sm font-medium text-gray-700 mb-1">
          AMT: incentive-stock-option spread (annual)
        </label>
        <input
          id="amt-iso"
          type="number"
          min="0"
          step="1000"
          inputMode="decimal"
          value={iso}
          onChange={(e) => {
            setIso(e.target.value)
            setSaved(false)
            setError(null)
          }}
          placeholder="0"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p className="mt-1 text-xs text-gray-400">
          The bargain element from exercising and holding incentive stock options this year, an AMT
          preference. Leave blank if none. Together with the SALT add-back, this is what can make
          the AMT line appear on your Cash Flow estimate.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      {saved && (
        <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
          Household tax settings saved.
        </p>
      )}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!hasChanges || update.isPending}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {update.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  )
}

export default function SettingsHousehold() {
  const isPrimary = useAuth((s) => s.role === "primary")

  const {
    data: household,
    isLoading,
    error: loadError,
  } = useQuery({
    queryKey: ["household"],
    queryFn: householdApi.get,
  })

  return (
    <div className="p-8 max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Household &amp; tax</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Your household's filing status, state of residence, and AMT preference items. These feed
          the tax estimates on the Cash Flow report (federal brackets, state income tax, NIIT, and
          the alternative minimum tax).
        </p>
      </div>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
      {loadError && (
        <div className="text-sm text-red-500 py-4">Failed to load household settings.</div>
      )}

      {household && !isPrimary && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-2">
          <p className="text-sm text-gray-600">
            Filing status:{" "}
            <span className="font-medium text-gray-900">
              {FILING_STATUS_OPTIONS.find((o) => o.value === household.filing_status)?.label ??
                "Not set"}
            </span>
          </p>
          <p className="text-sm text-gray-600">
            State of residence:{" "}
            <span className="font-medium text-gray-900">{household.state ?? "Not set"}</span>
          </p>
          <p className="text-sm text-gray-600">
            AMT state/local add-back:{" "}
            <span className="font-medium text-gray-900">
              {household.amt_salt_preference ?? "Not set"}
            </span>
          </p>
          <p className="text-sm text-gray-600">
            AMT incentive-stock-option spread:{" "}
            <span className="font-medium text-gray-900">
              {household.amt_iso_preference ?? "Not set"}
            </span>
          </p>
          <p className="text-xs text-gray-400 pt-1">
            Only a primary member can change household tax settings.
          </p>
        </div>
      )}

      {household && isPrimary && <HouseholdTaxForm household={household} />}
    </div>
  )
}
