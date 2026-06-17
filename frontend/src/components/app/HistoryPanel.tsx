import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { auditLogApi } from "@/api/auditLog"
import type { AuditLogEntryResponse } from "@/api/types"

function formatAction(action: string): string {
  return action.replace(/\./g, " › ").replace(/_/g, " ")
}

function AuditRow({ entry }: { entry: AuditLogEntryResponse }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetail = entry.previous_value || entry.new_value

  return (
    <div className="px-4 py-2 text-sm border-b border-gray-100 last:border-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <span className="font-medium text-gray-800">{formatAction(entry.action)}</span>
          {entry.user_display_name && (
            <span className="ml-2 text-gray-500">by {entry.user_display_name}</span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-gray-400">
            {new Date(entry.created_at).toLocaleString("en-US", {
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            })}
          </span>
          {hasDetail && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-xs text-indigo-600 hover:text-indigo-800"
            >
              {expanded ? "hide" : "diff"}
            </button>
          )}
        </div>
      </div>
      {expanded && (
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          {entry.previous_value && (
            <div>
              <p className="font-semibold text-gray-500 mb-1">Before</p>
              <pre className="bg-red-50 rounded p-2 overflow-auto whitespace-pre-wrap text-gray-700">
                {JSON.stringify(entry.previous_value, null, 2)}
              </pre>
            </div>
          )}
          {entry.new_value && (
            <div>
              <p className="font-semibold text-gray-500 mb-1">After</p>
              <pre className="bg-green-50 rounded p-2 overflow-auto whitespace-pre-wrap text-gray-700">
                {JSON.stringify(entry.new_value, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function HistoryPanel({ entityType, entityId }: { entityType: string; entityId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-log", entityType, entityId],
    queryFn: () => auditLogApi.list({ entity_type: entityType, entity_id: entityId }),
  })

  if (isLoading) return <div className="px-4 py-3 text-sm text-gray-400">Loading history…</div>
  if (error) return <div className="px-4 py-3 text-sm text-red-500">Failed to load history.</div>
  if (!data || data.items.length === 0)
    return <div className="px-4 py-3 text-sm text-gray-400">No history yet.</div>

  return (
    <div className="bg-gray-50 rounded-xl border border-gray-200">
      {data.items.map((entry) => (
        <AuditRow key={entry.id} entry={entry} />
      ))}
    </div>
  )
}
