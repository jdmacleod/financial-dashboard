import { useQuery } from "@tanstack/react-query"
import { equityGrantsApi } from "@/api/equityGrants"
import { formatCurrency } from "@/lib/formatters"

const GRANT_TYPE_LABELS: Record<string, string> = {
  rsu: "RSU",
  iso: "ISO",
  nso: "NSO",
  espp: "ESPP",
}

export function EquityGrantsPanel() {
  const query = useQuery({
    queryKey: ["equity-grants"],
    queryFn: () => equityGrantsApi.list(),
  })

  const grants = query.data
  if (!grants || grants.length === 0) return null

  return (
    <section>
      <div
        className="mb-2 text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--faint)" }}
      >
        Equity compensation
      </div>
      <div className="space-y-3">
        {grants.map((grant) => {
          const totalIncome = grant.vesting_events.reduce(
            (sum, e) => sum + Number(e.taxable_ordinary_income),
            0,
          )
          const hasAmt = grant.vesting_events.some(
            (e) => e.amt_preference_amount !== null && Number(e.amt_preference_amount) > 0,
          )
          return (
            <div
              key={grant.id}
              className="rounded-lg border p-4"
              style={{ borderColor: "var(--bd)", background: "var(--card)" }}
            >
              <div className="flex items-baseline justify-between">
                <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  {grant.ticker}
                  <span
                    className="ml-2 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase"
                    style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
                  >
                    {GRANT_TYPE_LABELS[grant.grant_type] ?? grant.grant_type}
                  </span>
                  {hasAmt && (
                    <span
                      className="ml-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase"
                      style={{ background: "var(--nav-active-bg)", color: "var(--liab)" }}
                    >
                      AMT
                    </span>
                  )}
                </div>
                <div className="text-xs" style={{ color: "var(--faint)" }}>
                  {Number(grant.shares_granted).toLocaleString()} shares granted
                </div>
              </div>
              <div className="mt-1 text-xs" style={{ color: "var(--label)" }}>
                {grant.vesting_events.length} vesting event
                {grant.vesting_events.length !== 1 ? "s" : ""}
                {totalIncome > 0 && <> · {formatCurrency(String(totalIncome))} vested income</>}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
