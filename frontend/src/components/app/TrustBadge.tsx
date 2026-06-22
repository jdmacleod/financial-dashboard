import { Landmark } from "lucide-react"

/**
 * Compact pill marking an account/asset that is titled to an ownership entity
 * (revocable trust, ILIT, LLC, custodial account, …). Uses inline styles to
 * match the Accounts/Assets pages, which are not Tailwind-class based.
 */
export function TrustBadge({ name, title }: { name: string; title?: string }) {
  return (
    <span
      title={title ?? name}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        padding: "1px 7px",
        borderRadius: "999px",
        background: "var(--nav-active-bg)",
        color: "var(--label)",
        fontSize: "10px",
        fontWeight: 500,
        maxWidth: "100%",
        overflow: "hidden",
      }}
    >
      <Landmark size={11} style={{ flexShrink: 0 }} />
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {name}
      </span>
    </span>
  )
}
