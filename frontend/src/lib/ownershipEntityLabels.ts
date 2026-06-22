// Display labels for ownership-entity types (mirrors the backend
// OWNERSHIP_ENTITY_TYPES enum). Used by the estate-exposure panel and trust
// badges. Falls back to a title-cased slug for any unmapped value.
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

export function ownershipEntityTypeLabel(slug: string | null): string {
  if (!slug) return "Directly owned"
  return (
    ENTITY_TYPE_LABELS[slug] ??
    slug
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  )
}
