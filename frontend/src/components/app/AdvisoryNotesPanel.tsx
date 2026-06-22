import { useQuery } from "@tanstack/react-query"
import { advisoryNotesApi } from "@/api/advisoryNotes"
import { advisoryCategoryMeta } from "@/lib/advisoryCategories"

interface AdvisoryNotesPanelProps {
  accountId?: string
  ownershipEntityId?: string
  heading?: string
}

/**
 * Shows advisory notes anchored to a specific account or ownership entity.
 * Renders nothing while loading, on error, or when there are no anchored notes,
 * so it can be dropped into any detail view without adding clutter.
 */
export function AdvisoryNotesPanel({
  accountId,
  ownershipEntityId,
  heading = "Advisory notes",
}: AdvisoryNotesPanelProps) {
  const query = useQuery({
    queryKey: ["advisory-notes", { accountId, ownershipEntityId }],
    queryFn: () =>
      advisoryNotesApi.list({
        account_id: accountId,
        ownership_entity_id: ownershipEntityId,
      }),
    enabled: Boolean(accountId || ownershipEntityId),
  })

  const notes = query.data
  if (!notes || notes.length === 0) return null

  return (
    <div
      className="rounded-lg border p-4"
      style={{ borderColor: "var(--bd)", background: "var(--card)" }}
    >
      <div
        className="mb-2 text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--faint)" }}
      >
        {heading}
      </div>
      <div className="space-y-3">
        {notes.map((note) => {
          const meta = advisoryCategoryMeta(note.category)
          const Icon = meta.Icon
          return (
            <div
              key={note.id}
              style={
                meta.emphasis
                  ? { borderLeft: `2px solid ${meta.accent}`, paddingLeft: "8px" }
                  : undefined
              }
            >
              <div className="flex items-center gap-2">
                <span
                  className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide"
                  style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
                >
                  <Icon size={11} style={{ color: meta.accent }} />
                  {meta.label}
                </span>
                <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                  {note.title}
                </span>
              </div>
              <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--label)" }}>
                {note.body}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
