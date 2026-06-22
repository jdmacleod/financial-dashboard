import {
  AlertTriangle,
  FileText,
  HeartHandshake,
  Info,
  Landmark,
  Receipt,
  Shield,
  Sunrise,
  type LucideIcon,
} from "lucide-react"

// Shared display metadata for advisory-note categories, used by the Insights
// page, the per-entity/account panels, and the dashboard teaser so labels,
// icons, and accent colors stay consistent everywhere.
export interface AdvisoryCategoryMeta {
  label: string
  Icon: LucideIcon
  accent: string
  // Risk / informational categories that warrant visual emphasis.
  emphasis: boolean
}

export const ADVISORY_CATEGORY_ORDER = [
  "estate",
  "tax",
  "concentration",
  "insurance",
  "retirement",
  "charitable",
  "scope_omission",
]

const META: Record<string, AdvisoryCategoryMeta> = {
  estate: { label: "Estate", Icon: Landmark, accent: "var(--color-blue)", emphasis: false },
  tax: { label: "Tax", Icon: Receipt, accent: "var(--color-gold)", emphasis: false },
  concentration: {
    label: "Concentration",
    Icon: AlertTriangle,
    accent: "var(--liab)",
    emphasis: true,
  },
  insurance: { label: "Insurance", Icon: Shield, accent: "var(--color-green)", emphasis: false },
  retirement: {
    label: "Retirement",
    Icon: Sunrise,
    accent: "var(--color-bronze)",
    emphasis: false,
  },
  charitable: {
    label: "Charitable",
    Icon: HeartHandshake,
    accent: "var(--color-green)",
    emphasis: false,
  },
  scope_omission: {
    label: "Scope & Omissions",
    Icon: Info,
    accent: "var(--faint)",
    emphasis: true,
  },
}

function titleCase(slug: string): string {
  return slug
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
}

export function advisoryCategoryMeta(slug: string): AdvisoryCategoryMeta {
  return (
    META[slug] ?? {
      label: titleCase(slug),
      Icon: FileText,
      accent: "var(--muted)",
      emphasis: false,
    }
  )
}

export function advisoryCategoryLabel(slug: string): string {
  return advisoryCategoryMeta(slug).label
}
