import { useQuery } from "@tanstack/react-query"
import { advisoryNotesApi } from "@/api/advisoryNotes"

const CATEGORY_LABELS: Record<string, string> = {
  estate: "Estate",
  tax: "Tax",
  concentration: "Concentration",
  insurance: "Insurance",
  retirement: "Retirement",
  charitable: "Charitable",
  scope_omission: "Scope & Omissions",
}

function categoryLabel(slug: string): string {
  return (
    CATEGORY_LABELS[slug] ??
    slug
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  )
}

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
        {notes.map((note) => (
          <div key={note.id}>
            <div className="flex items-baseline gap-2">
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide"
                style={{ background: "var(--nav-active-bg)", color: "var(--label)" }}
              >
                {categoryLabel(note.category)}
              </span>
              <span className="text-sm font-semibold" style={{ color: "var(--text)" }}>
                {note.title}
              </span>
            </div>
            <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--label)" }}>
              {note.body}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
