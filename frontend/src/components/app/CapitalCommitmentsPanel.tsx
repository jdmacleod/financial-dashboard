import { useQuery } from "@tanstack/react-query"
import { capitalCommitmentsApi } from "@/api/capitalCommitments"
import { formatCurrency } from "@/lib/formatters"

export function CapitalCommitmentsPanel() {
  const query = useQuery({
    queryKey: ["capital-commitments"],
    queryFn: () => capitalCommitmentsApi.list(),
  })

  const commitments = query.data
  if (!commitments || commitments.length === 0) return null

  return (
    <section>
      <div
        className="mb-2 text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--faint)" }}
      >
        Private-fund commitments
      </div>
      <div className="space-y-3">
        {commitments.map((c) => {
          const committed = Number(c.committed_amount)
          const called = Number(c.called_to_date)
          const pct = committed > 0 ? Math.min(100, Math.round((called / committed) * 100)) : 0
          return (
            <div
              key={c.id}
              className="rounded-lg border p-4"
              style={{ borderColor: "var(--bd)", background: "var(--card)" }}
            >
              <div className="flex items-baseline justify-between">
                <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  {c.fund_name}
                </span>
                <span className="text-xs" style={{ color: "var(--faint)" }}>
                  Vintage {c.vintage_year}
                </span>
              </div>
              <div
                className="mt-2 h-1.5 w-full overflow-hidden rounded-full"
                style={{ background: "var(--bd)" }}
              >
                <div
                  className="h-full rounded-full"
                  style={{ width: `${pct}%`, background: "var(--accent, #6c97c4)" }}
                />
              </div>
              <div className="mt-1.5 text-xs" style={{ color: "var(--label)" }}>
                {formatCurrency(c.called_to_date)} called of {formatCurrency(c.committed_amount)}{" "}
                committed ({pct}%)
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
