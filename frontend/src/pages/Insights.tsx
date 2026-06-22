import { useQuery } from "@tanstack/react-query"
import { advisoryNotesApi } from "@/api/advisoryNotes"
import { QueryGuard } from "@/components/app/QueryGuard"
import { formatDate } from "@/lib/formatters"
import type { AdvisoryNoteResponse } from "@/api/types"

// Display labels + ordering for advisory-note categories. Unknown categories
// fall back to a title-cased version of the raw slug.
const CATEGORY_LABELS: Record<string, string> = {
  estate: "Estate",
  tax: "Tax",
  concentration: "Concentration",
  insurance: "Insurance",
  retirement: "Retirement",
  charitable: "Charitable",
  scope_omission: "Scope & Omissions",
}
const CATEGORY_ORDER = [
  "estate",
  "tax",
  "concentration",
  "insurance",
  "retirement",
  "charitable",
  "scope_omission",
]

function categoryLabel(slug: string): string {
  return (
    CATEGORY_LABELS[slug] ??
    slug
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  )
}

function groupByCategory(notes: AdvisoryNoteResponse[]): [string, AdvisoryNoteResponse[]][] {
  const groups = new Map<string, AdvisoryNoteResponse[]>()
  for (const note of notes) {
    const list = groups.get(note.category) ?? []
    list.push(note)
    groups.set(note.category, list)
  }
  const known = CATEGORY_ORDER.filter((c) => groups.has(c))
  const extra = [...groups.keys()].filter((c) => !CATEGORY_ORDER.includes(c)).sort()
  return [...known, ...extra].map((c) => [c, groups.get(c)!])
}

export default function Insights() {
  const query = useQuery({
    queryKey: ["advisory-notes"],
    queryFn: () => advisoryNotesApi.list(),
  })

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-1 text-xl font-semibold" style={{ color: "var(--text)" }}>
        Insights
      </h1>
      <p className="mb-6 text-sm" style={{ color: "var(--label)" }}>
        Planning notes surfaced from your household's financial structure.
      </p>

      <QueryGuard
        query={query}
        empty={
          <div
            className="rounded-lg border border-dashed p-8 text-center text-sm"
            style={{ color: "var(--label)" }}
          >
            No advisory notes yet.
          </div>
        }
      >
        {(notes) => (
          <div className="space-y-8">
            {groupByCategory(notes).map(([category, items]) => (
              <section key={category}>
                <div
                  className="mb-2 text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--faint)" }}
                >
                  {categoryLabel(category)}
                </div>
                <div className="space-y-3">
                  {items.map((note) => (
                    <article
                      key={note.id}
                      className="rounded-lg border p-4"
                      style={{ borderColor: "var(--bd)", background: "var(--card)" }}
                    >
                      <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                        {note.title}
                      </h2>
                      <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--label)" }}>
                        {note.body}
                      </p>
                      <div className="mt-2 text-xs" style={{ color: "var(--faint)" }}>
                        {formatDate(note.created_at)}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryGuard>
    </div>
  )
}
