import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { backupsApi } from "@/api/backups"
import type { BackupJobResponse } from "@/api/types"
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

function formatBytes(bytes: number | null) {
  if (bytes == null) return "—"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function BackupRow({ job }: { job: BackupJobResponse }) {
  return (
    <tr className="border-t border-gray-100 dark:border-gray-700">
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
        {format(parseISO(job.started_at), "MMM d, yyyy HH:mm")}
      </td>
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 capitalize">
        {job.triggered_by}
      </td>
      <td className="px-4 py-3">{statusBadge(job.status)}</td>
      <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">
        {formatBytes(job.file_size_bytes)}
      </td>
      <td className="px-4 py-3 text-sm">
        {job.status === "complete" && job.filename ? (
          <a
            href={backupsApi.downloadUrl(job.id)}
            download={job.filename}
            className="text-indigo-600 hover:underline dark:text-indigo-400"
          >
            Download
          </a>
        ) : job.error_message ? (
          <span className="text-red-600 dark:text-red-400 text-xs" title={job.error_message}>
            Error
          </span>
        ) : (
          <span className="text-gray-400 dark:text-gray-500">—</span>
        )}
      </td>
    </tr>
  )
}

export default function SettingsBackups() {
  const queryClient = useQueryClient()
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["backups"],
    queryFn: backupsApi.list,
    refetchInterval: 10_000,
  })

  const trigger = useMutation({
    mutationFn: backupsApi.trigger,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backups"] }),
  })

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Backups</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manual and scheduled database backups.
          </p>
        </div>
        <button
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending}
          className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {trigger.isPending ? "Starting…" : "Run backup now"}
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <p className="p-6 text-sm text-gray-500 dark:text-gray-400">Loading…</p>
        ) : jobs.length === 0 ? (
          <p className="p-6 text-sm text-gray-500 dark:text-gray-400">No backups yet.</p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                <th className="px-4 py-3">Started</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <BackupRow key={j.id} job={j} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
