import { Shield } from "lucide-react"

/**
 * Compact pill marking a real estate asset that has a linked insurance policy.
 * Uses emerald/teal to distinguish from the indigo TrustBadge.
 */
export function InsuranceBadge({ label, carrier }: { label: string; carrier?: string | null }) {
  const displayText = carrier ? `${label} · ${carrier}` : label
  return (
    <span
      title={displayText}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: "1px 7px",
        borderRadius: "999px",
        background: "rgba(5, 150, 105, 0.09)",
        color: "#047857",
        border: "1px solid rgba(5, 150, 105, 0.2)",
        fontSize: "10px",
        fontWeight: 500,
        maxWidth: "100%",
        overflow: "hidden",
      }}
    >
      <Shield size={11} style={{ flexShrink: 0 }} />
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {displayText}
      </span>
    </span>
  )
}
