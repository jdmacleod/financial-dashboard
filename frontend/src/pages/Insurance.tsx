import { useQuery } from "@tanstack/react-query"
import { insurancePoliciesApi } from "@/api/insurancePolicies"
import { QueryGuard } from "@/components/app/QueryGuard"
import { formatCurrency } from "@/lib/formatters"

const POLICY_TYPE_LABELS: Record<string, string> = {
  term_life: "Term Life",
  permanent_life: "Permanent Life",
  umbrella_liability: "Umbrella Liability",
  disability: "Disability",
  long_term_care: "Long-Term Care",
  scheduled_specialty: "Scheduled / Specialty",
}

const CADENCE_LABELS: Record<string, string> = {
  monthly: "/mo",
  quarterly: "/qtr",
  annual: "/yr",
}

function policyTypeLabel(slug: string): string {
  return (
    POLICY_TYPE_LABELS[slug] ??
    slug
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  )
}

export default function Insurance() {
  const query = useQuery({
    queryKey: ["insurance-policies"],
    queryFn: () => insurancePoliciesApi.list(),
  })

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-1 text-xl font-semibold" style={{ color: "var(--text)" }}>
        Insurance
      </h1>
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
            No insurance policies yet.
          </div>
        }
      >
        {(policies) => (
          <div className="space-y-3">
            {policies.map((p) => (
              <div
                key={p.id}
                className="rounded-lg border p-4"
                style={{ borderColor: "var(--bd)", background: "var(--card)" }}
              >
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    {policyTypeLabel(p.policy_type)}
                  </span>
                  <span className="text-sm" style={{ color: "var(--label)" }}>
                    {formatCurrency(p.premium_amount)}
                    {CADENCE_LABELS[p.premium_cadence] ?? ""}
                  </span>
                </div>
                <div className="mt-1 text-sm" style={{ color: "var(--label)" }}>
                  {formatCurrency(p.coverage_amount)} coverage
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {p.owner_ownership_entity_id && (
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-medium"
                      style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
                    >
                      Trust-owned (outside estate)
                    </span>
                  )}
                  {p.cash_value_account_id && (
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-medium"
                      style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
                    >
                      Cash value in net worth
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </QueryGuard>
    </div>
  )
}
