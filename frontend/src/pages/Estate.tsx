import { useQuery } from "@tanstack/react-query"
import { ownershipEntitiesApi } from "@/api/ownershipEntities"
import { AdvisoryNotesPanel } from "@/components/app/AdvisoryNotesPanel"
import { QueryGuard } from "@/components/app/QueryGuard"

const ENTITY_TYPE_LABELS: Record<string, string> = {
  revocable_trust: "Revocable Trust",
  irrevocable_trust: "Irrevocable Trust",
  ilit: "ILIT",
  crt_crat: "Charitable Remainder Annuity Trust",
  crt_crut: "Charitable Remainder Unitrust",
  clt: "Charitable Lead Trust",
  llc: "LLC",
  custodial_utma: "UTMA Custodial",
  custodial_ugma: "UGMA Custodial",
}

function entityTypeLabel(slug: string): string {
  return (
    ENTITY_TYPE_LABELS[slug] ??
    slug
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  )
}

function Badge({ on, onText, offText }: { on: boolean; onText: string; offText: string }) {
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        background: on ? "var(--nav-active-bg)" : "transparent",
        border: on ? "none" : "1px solid var(--bd)",
        color: on ? "var(--text)" : "var(--faint)",
      }}
    >
      {on ? onText : offText}
    </span>
  )
}

export default function Estate() {
  const query = useQuery({
    queryKey: ["ownership-entities"],
    queryFn: () => ownershipEntitiesApi.list(),
  })

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-1 text-xl font-semibold" style={{ color: "var(--text)" }}>
        Estate &amp; structure
      </h1>
      <p className="mb-6 text-sm" style={{ color: "var(--label)" }}>
        Trusts and titling entities, and how each one affects your net worth and taxable estate.
      </p>

      <QueryGuard
        query={query}
        empty={
          <div
            className="rounded-lg border border-dashed p-8 text-center text-sm"
            style={{ color: "var(--label)" }}
          >
            No trusts or titling entities yet.
          </div>
        }
      >
        {(entities) => (
          <div className="space-y-4">
            {entities.map((entity) => (
              <div key={entity.id} className="space-y-3">
                <div
                  className="rounded-lg border p-4"
                  style={{ borderColor: "var(--bd)", background: "var(--card)" }}
                >
                  <div className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                    {entity.name}
                  </div>
                  <div className="mt-0.5 text-xs" style={{ color: "var(--faint)" }}>
                    {entityTypeLabel(entity.entity_type)}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Badge
                      on={entity.counts_in_personal_net_worth}
                      onText="In net worth"
                      offText="Excluded from net worth"
                    />
                    <Badge
                      on={entity.is_in_taxable_estate}
                      onText="In taxable estate"
                      offText="Outside taxable estate"
                    />
                  </div>
                </div>
                <AdvisoryNotesPanel ownershipEntityId={entity.id} />
              </div>
            ))}
          </div>
        )}
      </QueryGuard>
    </div>
  )
}
