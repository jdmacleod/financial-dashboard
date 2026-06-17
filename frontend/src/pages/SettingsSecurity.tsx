import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { auditLogApi } from "@/api/auditLog"
import type { AuditLogEntryResponse } from "@/api/types"

function SecurityRow({ entry }: { entry: AuditLogEntryResponse }) {
  const isSuccess = entry.action.includes("success") || entry.action === "auth.login"
  const isFailure =
    entry.action.includes("fail") ||
    entry.action.includes("lock") ||
    entry.action.includes("invalid")

  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 last:border-0">
      <div
        className={`h-2 w-2 rounded-full shrink-0 ${
          isFailure ? "bg-red-500" : isSuccess ? "bg-emerald-500" : "bg-gray-300"
        }`}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">
          {entry.action.replace(/\./g, " › ").replace(/_/g, " ")}
        </p>
        {entry.user_display_name && (
          <p className="text-xs text-gray-500">{entry.user_display_name}</p>
        )}
      </div>
      <div className="text-right shrink-0">
        <p className="text-xs text-gray-400">
          {new Date(entry.created_at).toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </p>
        {entry.ip_address && <p className="text-xs text-gray-400">{entry.ip_address}</p>}
      </div>
    </div>
  )
}

export default function SettingsSecurity() {
  const [page, setPage] = useState(1)

  const { data, isLoading, error } = useQuery({
    queryKey: ["audit-log", "security", page],
    queryFn: () => auditLogApi.list({ entity_type: "auth", page, page_size: 50 }),
  })

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 50)) : 1

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Security Log</h1>
        <p className="text-sm text-gray-500 mt-1">
          Authentication events. You see your own events; primary members see all.
        </p>
      </div>

      {isLoading && <div className="text-sm text-gray-400">Loading…</div>}
      {error && <div className="text-sm text-red-500">Failed to load security log.</div>}

      {data && (
        <>
          <div className="bg-white rounded-xl border border-gray-200">
            {data.items.length > 0 ? (
              data.items.map((entry) => <SecurityRow key={entry.id} entry={entry} />)
            ) : (
              <p className="px-4 py-8 text-center text-gray-400">No security events found.</p>
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
