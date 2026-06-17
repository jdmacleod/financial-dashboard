import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { auditLogApi } from "@/api/auditLog"
import { membersApi } from "@/api/members"
import { useAuth } from "@/hooks/useAuth"
import type { AuditLogEntryResponse } from "@/api/types"

function formatAction(action: string): string {
  return action.replace(/\./g, " › ").replace(/_/g, " ")
}

function AuditRow({ entry }: { entry: AuditLogEntryResponse }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetail = entry.previous_value || entry.new_value

  return (
    <div className="px-4 py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-gray-800">{formatAction(entry.action)}</span>
          {entry.entity_id && (
            <span className="ml-2 text-xs text-gray-400">#{entry.entity_id.slice(0, 8)}</span>
          )}
          {entry.user_display_name && (
            <span className="ml-2 text-xs text-indigo-600">{entry.user_display_name}</span>
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
      {entry.ip_address && <p className="text-xs text-gray-400 mt-0.5">IP: {entry.ip_address}</p>}
      {expanded && (
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          {entry.previous_value && (
            <div>
              <p className="font-semibold text-gray-500 mb-1">Before</p>
              <pre className="bg-red-50 rounded p-2 overflow-auto whitespace-pre-wrap text-gray-700 max-h-40">
                {JSON.stringify(entry.previous_value, null, 2)}
              </pre>
            </div>
          )}
          {entry.new_value && (
            <div>
              <p className="font-semibold text-gray-500 mb-1">After</p>
              <pre className="bg-green-50 rounded p-2 overflow-auto whitespace-pre-wrap text-gray-700 max-h-40">
                {JSON.stringify(entry.new_value, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const ENTITY_TYPES = [
  "account",
  "transaction",
  "category",
  "budget",
  "member",
  "real_estate_property",
  "access_grant",
]

export default function SettingsActivity() {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [memberId, setMemberId] = useState("")
  const [entityType, setEntityType] = useState("")
  const [page, setPage] = useState(1)

  const { data: members } = useQuery({
    queryKey: ["members"],
    queryFn: membersApi.list,
    enabled: isPrimary,
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-log", "activity", { memberId, entityType, page }],
    queryFn: () =>
      auditLogApi.list({
        member_id: memberId || undefined,
        entity_type: entityType || undefined,
        page,
        page_size: 50,
      }),
    enabled: isPrimary,
  })

  if (!isPrimary) {
    return (
      <div className="p-8 max-w-3xl mx-auto">
        <h1 className="text-2xl font-semibold mb-4">Activity Log</h1>
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-8 text-center">
          <p className="text-amber-700 font-medium">Primary member access only.</p>
        </div>
      </div>
    )
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 50)) : 1

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Activity Log</h1>

      <div className="flex flex-wrap gap-3">
        <select
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value)
            setPage(1)
          }}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All types</option>
          {ENTITY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        {members && (
          <select
            value={memberId}
            onChange={(e) => {
              setMemberId(e.target.value)
              setPage(1)
            }}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All members</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
        )}
        {(entityType || memberId) && (
          <button
            onClick={() => {
              setEntityType("")
              setMemberId("")
              setPage(1)
            }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Clear filters
          </button>
        )}
      </div>

      {isLoading && <div className="text-sm text-gray-400">Loading…</div>}
      {error && <div className="text-sm text-red-500">Failed to load audit log.</div>}

      {data && (
        <>
          <div className="bg-white rounded-xl border border-gray-200">
            {data.items.length > 0 ? (
              data.items.map((entry) => <AuditRow key={entry.id} entry={entry} />)
            ) : (
              <p className="px-4 py-8 text-center text-gray-400">No activity found.</p>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
