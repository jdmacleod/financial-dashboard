import { useQuery } from "@tanstack/react-query"
import { investmentLotsApi } from "@/api/investmentLots"
import { formatCurrency, formatDate } from "@/lib/formatters"

const BASIS_TYPE_LABELS: Record<string, string> = {
  purchase: "Purchase",
  rsu_vest: "RSU vest",
  espp: "ESPP",
  inherited_stepup: "Inherited (step-up)",
  gift_carryover: "Gift (carryover)",
  reinvested_dividend: "Reinvested dividend",
}

export function InvestmentLotsPanel({ accountId }: { accountId?: string }) {
  const query = useQuery({
    queryKey: ["investment-lots", { accountId }],
    queryFn: () => investmentLotsApi.list(accountId ? { account_id: accountId } : undefined),
  })

  const lots = query.data
  if (!lots || lots.length === 0) return null

  return (
    <section>
      <div
        className="mb-2 text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--faint)" }}
      >
        Cost-basis lots
      </div>
      <div
        className="overflow-hidden rounded-lg border"
        style={{ borderColor: "var(--bd)", background: "var(--card)" }}
      >
        {lots.map((lot, i) => (
          <div
            key={lot.id}
            className="flex items-center justify-between px-4 py-2.5 text-sm"
            style={{ borderTop: i === 0 ? "none" : "1px solid var(--bd)" }}
          >
            <div>
              <span className="font-semibold" style={{ color: "var(--text)" }}>
                {lot.ticker}
              </span>
              <span
                className="ml-2 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
              >
                {BASIS_TYPE_LABELS[lot.basis_type] ?? lot.basis_type}
              </span>
            </div>
            <div className="text-right" style={{ color: "var(--label)" }}>
              <div>
                {Number(lot.shares).toLocaleString()} @ {formatCurrency(lot.basis_per_share)}
              </div>
              <div className="text-xs" style={{ color: "var(--faint)" }}>
                acquired {formatDate(lot.acquired_date)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
