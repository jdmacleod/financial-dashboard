import { useQuery } from "@tanstack/react-query"
import { reportsApi } from "@/api/reports"
import { formatCurrency, formatDate } from "@/lib/formatters"
import type { MemberRequiredDistribution } from "@/api/types"

function MemberCard({ m }: { m: MemberRequiredDistribution }) {
  const started = m.has_started && m.rmd_amount !== null
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-semibold text-gray-900">{m.display_name}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {m.current_age !== null ? `Age ${m.current_age}` : "Date of birth not set"}
            {m.rmd_start_age !== null && ` · RMDs at ${m.rmd_start_age}`}
          </p>
        </div>
        {started && (
          <div className="text-right">
            <p className="text-xs text-gray-500">Required this year</p>
            <p className="text-2xl font-semibold text-indigo-600">
              {formatCurrency(m.rmd_amount as string)}
            </p>
          </div>
        )}
      </div>

      {started ? (
        <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-gray-100 pt-4 text-sm">
          <div>
            <dt className="text-xs text-gray-500">Pretax year-end balance</dt>
            <dd className="font-medium text-gray-900">
              {formatCurrency(m.pretax_balance as string)}
            </dd>
            {m.balance_as_of && (
              <dd className="text-xs text-gray-400">as of {formatDate(m.balance_as_of)}</dd>
            )}
          </div>
          <div>
            <dt className="text-xs text-gray-500">IRS Uniform Lifetime divisor</dt>
            <dd className="font-medium text-gray-900">{m.divisor}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">
          {m.note ?? "No required distribution this year."}
        </p>
      )}
    </div>
  )
}

export default function ReportRequiredDistributions() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "required-distributions"],
    queryFn: () => reportsApi.requiredDistributions(),
  })

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Required Minimum Distributions</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          The IRS amount each household member must withdraw from pretax retirement accounts once
          they reach RMD age{data ? ` (${data.year})` : ""}. Roth and taxable balances are never
          subject to RMDs.
        </p>
      </div>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
      {error && (
        <div className="text-sm text-red-500 py-4">Failed to load required distributions.</div>
      )}

      {data && data.members.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-sm text-gray-500">
            No pretax retirement accounts yet. RMDs apply to traditional 401(k), 403(b), and IRA
            balances — add one (and a year-end balance snapshot) to see projected distributions.
          </p>
        </div>
      )}

      {data && data.members.length > 0 && (
        <div className="space-y-4">
          {data.members.map((m) => (
            <MemberCard key={m.member_id} m={m} />
          ))}
        </div>
      )}
    </div>
  )
}
