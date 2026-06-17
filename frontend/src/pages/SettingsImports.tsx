import { useQuery } from "@tanstack/react-query"
import { importsApi } from "@/api/imports"
import type { ImportJobResponse } from "@/api/types"
import { format, parseISO } from "date-fns"

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    complete: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    processing: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    pending: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
  }
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? colors.pending}`}
    >
      {status}
    </span>
  )
}

function ImportRow({ job }: { job: ImportJobResponse }) {
  return (
    <tr className="border-t border-gray-100 dark:border-gray-700">
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
        {format(parseISO(job.created_at), "MMM d, yyyy HH:mm")}
      </td>
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 font-mono text-xs">
        {job.filename}
      </td>
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 uppercase text-xs">
        {job.format}
      </td>
      <td className="px-4 py-3">{statusBadge(job.status)}</td>
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
        {job.records_imported != null ? (
          <>
            {job.records_imported}
            {job.records_found != null && (
              <span className="text-gray-400"> / {job.records_found}</span>
            )}
          </>
        ) : (
          "—"
        )}
      </td>
      <td className="px-4 py-3 text-xs text-red-600 dark:text-red-400 max-w-xs truncate">
        {job.error_message ?? ""}
      </td>
    </tr>
  )
}

export default function SettingsImports() {
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["import-jobs"],
    queryFn: importsApi.listJobs,
  })

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Import History</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          All CSV and OFX/QFX imports for this household.
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500 dark:text-gray-400">Loading…</p>
        ) : jobs.length === 0 ? (
          <p className="p-6 text-sm text-gray-500 dark:text-gray-400">No imports yet.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">File</th>
                <th className="px-4 py-3">Format</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Records</th>
                <th className="px-4 py-3">Error</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <ImportRow key={j.id} job={j} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
