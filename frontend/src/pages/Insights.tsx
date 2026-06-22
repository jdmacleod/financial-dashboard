import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { advisoryNotesApi } from "@/api/advisoryNotes"
import { EstateExposurePanel } from "@/components/app/EstateExposurePanel"
import { QueryGuard } from "@/components/app/QueryGuard"
import { formatDate } from "@/lib/formatters"
import { ADVISORY_CATEGORY_ORDER, advisoryCategoryMeta } from "@/lib/advisoryCategories"
import type { AdvisoryNoteResponse } from "@/api/types"

function groupByCategory(notes: AdvisoryNoteResponse[]): [string, AdvisoryNoteResponse[]][] {
  const groups = new Map<string, AdvisoryNoteResponse[]>()
  for (const note of notes) {
    const list = groups.get(note.category) ?? []
    list.push(note)
    groups.set(note.category, list)
  }
  const known = ADVISORY_CATEGORY_ORDER.filter((c) => groups.has(c))
  const extra = [...groups.keys()].filter((c) => !ADVISORY_CATEGORY_ORDER.includes(c)).sort()
  return [...known, ...extra].map((c) => [c, groups.get(c)!])
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors"
      style={{
        background: active ? "var(--nav-active-bg)" : "transparent",
        border: `1px solid ${active ? "transparent" : "var(--bd)"}`,
        color: active ? "var(--text)" : "var(--label)",
      }}
    >
      {children}
    </button>
  )
}

export default function Insights() {
  const query = useQuery({
    queryKey: ["advisory-notes"],
    queryFn: () => advisoryNotesApi.list(),
  })
  const [active, setActive] = useState<string | null>(null)

  // Categories present in the data, in canonical order, for the filter row.
  const present = useMemo(() => {
    const set = new Set((query.data ?? []).map((n) => n.category))
    const known = ADVISORY_CATEGORY_ORDER.filter((c) => set.has(c))
    const extra = [...set].filter((c) => !ADVISORY_CATEGORY_ORDER.includes(c)).sort()
    return [...known, ...extra]
  }, [query.data])

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-1 text-xl font-semibold" style={{ color: "var(--text)" }}>
        Insights
      </h1>
      <p className="mb-4 text-sm" style={{ color: "var(--label)" }}>
        Planning notes surfaced from your household's financial structure.
      </p>

      <EstateExposurePanel />

      {present.length > 1 && (
        <div className="mb-6 flex flex-wrap gap-2">
          <FilterChip active={active === null} onClick={() => setActive(null)}>
            All
          </FilterChip>
          {present.map((cat) => {
            const meta = advisoryCategoryMeta(cat)
            const Icon = meta.Icon
            return (
              <FilterChip key={cat} active={active === cat} onClick={() => setActive(cat)}>
                <Icon size={12} style={{ color: meta.accent }} />
                {meta.label}
              </FilterChip>
            )
          })}
        </div>
      )}

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
        {(notes) => {
          const filtered = active ? notes.filter((n) => n.category === active) : notes
          return (
            <div className="space-y-8">
              {groupByCategory(filtered).map(([category, items]) => {
                const meta = advisoryCategoryMeta(category)
                const Icon = meta.Icon
                return (
                  <section key={category}>
                    <div
                      className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: meta.emphasis ? meta.accent : "var(--faint)" }}
                    >
                      <Icon size={13} style={{ color: meta.accent }} />
                      {meta.label}
                    </div>
                    <div className="space-y-3">
                      {items.map((note) => (
                        <article
                          key={note.id}
                          className="rounded-lg border p-4"
                          style={{
                            borderColor: "var(--bd)",
                            background: "var(--card)",
                            borderLeft: meta.emphasis ? `3px solid ${meta.accent}` : undefined,
                          }}
                        >
                          <h2 className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                            {note.title}
                          </h2>
                          <p
                            className="mt-1 text-sm leading-relaxed"
                            style={{ color: "var(--label)" }}
                          >
                            {note.body}
                          </p>
                          <div className="mt-2 text-xs" style={{ color: "var(--faint)" }}>
                            {formatDate(note.created_at)}
                          </div>
                        </article>
                      ))}
                    </div>
                  </section>
                )
              })}
            </div>
          )
        }}
      </QueryGuard>
    </div>
  )
}
