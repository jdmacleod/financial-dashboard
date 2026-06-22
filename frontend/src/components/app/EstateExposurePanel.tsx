import { useQuery } from "@tanstack/react-query"
import { Landmark, ShieldCheck, TriangleAlert } from "lucide-react"
import { reportsApi } from "@/api/reports"
import { formatCurrency } from "@/lib/formatters"
import { ownershipEntityTypeLabel } from "@/lib/ownershipEntityLabels"

function Stat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider" style={{ color: "var(--faint)" }}>
        {label}
      </div>
      <div className="mt-0.5 text-lg font-semibold" style={{ color: accent ?? "var(--text)" }}>
        {value}
      </div>
    </div>
  )
}

/**
 * Computed federal estate-exposure summary (gap #5): gross taxable estate vs.
 * the applicable exemption, plus a per-titling breakdown showing which holdings
 * sit inside the estate and which are sheltered (ILIT / irrevocable trust).
 * Renders nothing unless the household actually has estate structure to show —
 * sheltered assets or a taxable overage.
 */
export function EstateExposurePanel() {
  const { data } = useQuery({
    queryKey: ["estate-exposure"],
    queryFn: () => reportsApi.estateExposure(),
    staleTime: 60_000,
  })

  if (!data) return null
  const overage = Number(data.taxable_overage)
  const excluded = Number(data.excluded_from_estate)
  // Only relevant for households with estate structure: sheltered assets or
  // exposure above the exemption. Skip for simple, sub-exemption households.
  if (overage <= 0 && excluded === 0) return null

  const exposed = overage > 0
  const ratePct = Math.round(data.federal_estate_tax_rate * 100)

  return (
    <section
      className="mb-8 rounded-lg border p-4"
      style={{
        borderColor: "var(--bd)",
        background: "var(--card)",
        borderLeft: exposed ? "3px solid var(--liab, #e0b48a)" : undefined,
      }}
    >
      <div
        className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider"
        style={{ color: exposed ? "var(--liab, #e0b48a)" : "var(--faint)" }}
      >
        <Landmark size={13} />
        Estate exposure
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Gross taxable estate" value={formatCurrency(data.gross_taxable_estate)} />
        <Stat
          label={`Exemption (×${data.exemption_holders})`}
          value={formatCurrency(data.applicable_exemption)}
        />
        <Stat
          label="Over exemption"
          value={formatCurrency(data.taxable_overage)}
          accent={exposed ? "var(--liab, #e0b48a)" : undefined}
        />
        <Stat
          label={`Est. federal tax (${ratePct}%)`}
          value={formatCurrency(data.estimated_federal_estate_tax)}
          accent={exposed ? "var(--liab, #e0b48a)" : undefined}
        />
      </div>

      <div className="mt-3 flex items-center gap-1.5 text-xs" style={{ color: "var(--label)" }}>
        {exposed ? (
          <>
            <TriangleAlert size={12} style={{ color: "var(--liab, #e0b48a)" }} />
            Taxable estate exceeds the applicable exemption.
          </>
        ) : (
          <>
            <ShieldCheck size={12} style={{ color: "var(--ok, #7fae7f)" }} />
            Within the applicable exemption; {formatCurrency(data.excluded_from_estate)} held
            outside the estate.
          </>
        )}
      </div>

      {data.entities.length > 1 && (
        <div className="mt-4 space-y-1.5">
          {data.entities.map((e) => (
            <div
              key={e.entity_id ?? "owned"}
              className="flex items-center justify-between rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--nav-active-bg)" }}
            >
              <span className="flex items-center gap-2" style={{ color: "var(--text)" }}>
                {e.entity_name ?? "Directly owned"}
                <span
                  className="rounded-full px-1.5 py-0.5 text-[10px] uppercase tracking-wide"
                  style={{
                    background: "transparent",
                    border: "1px solid var(--bd)",
                    color: e.is_in_taxable_estate ? "var(--label)" : "var(--ok, #7fae7f)",
                  }}
                >
                  {e.is_in_taxable_estate
                    ? ownershipEntityTypeLabel(e.entity_type)
                    : `${ownershipEntityTypeLabel(e.entity_type)} · sheltered`}
                </span>
              </span>
              <span style={{ color: "var(--label)" }}>{formatCurrency(e.net_value)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
