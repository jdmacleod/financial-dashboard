import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { exportApi } from "@/api/exports"
import { authApi } from "@/api/auth"
import { ApiError } from "@/api/client"
import type { ExportJobResponse, ExportJobStatus, ExportType } from "@/api/types"

const TYPE_LABELS: Record<ExportType, string> = {
  pdf_summary: "PDF Summary",
  pdf_executor: "PDF Full",
  excel_summary: "Excel Summary",
  excel_executor: "Excel Full",
}

const STATUS_CLASSES: Record<ExportJobStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  complete: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
}

function isInProgress(status: ExportJobStatus): boolean {
  return status === "pending" || status === "processing"
}

function shortId(id: string): string {
  return id.slice(0, 8) + "…"
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function DownloadButton({ job }: { job: ExportJobResponse }) {
  const isExecutor = job.export_type === "pdf_executor" || job.export_type === "excel_executor"
  const [showReauth, setShowReauth] = useState(false)
  const [password, setPassword] = useState("")
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function doDownload(reauthToken?: string) {
    setDownloading(true)
    setError(null)
    try {
      const blob = await exportApi.download(job.id, reauthToken)
      const ext = job.export_type.startsWith("pdf") ? "pdf" : "xlsx"
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = job.filename ?? `hearthledger-export.${ext}`
      a.click()
      URL.revokeObjectURL(url)
      setShowReauth(false)
      setPassword("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.")
    } finally {
      setDownloading(false)
    }
  }

  async function handleReauthDownload() {
    try {
      const res = await authApi.reauth(password)
      await doDownload(res.reauth_token)
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : "Authentication failed.")
    }
  }

  if (isExecutor && showReauth) {
    return (
      <div className="flex flex-col gap-1.5 min-w-[200px]">
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !downloading && handleReauthDownload()}
          placeholder="Your password"
          className="rounded border border-gray-300 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex gap-1">
          <button
            onClick={() => {
              setShowReauth(false)
              setError(null)
            }}
            className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleReauthDownload}
            disabled={downloading || !password}
            className="flex-1 rounded bg-indigo-600 px-2 py-1 text-xs text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {downloading ? "…" : "Download"}
          </button>
        </div>
      </div>
    )
  }

  return (
    <button
      onClick={() => (isExecutor ? setShowReauth(true) : doDownload())}
      disabled={downloading}
      className="rounded bg-indigo-600 px-3 py-1 text-xs text-white hover:bg-indigo-700 disabled:opacity-60"
    >
      {downloading ? "Downloading…" : "Download"}
    </button>
  )
}

export default function ExportsHistory() {
  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["exports"],
    queryFn: () => exportApi.list(),
    refetchInterval: (query) => {
      const data = query.state.data as ExportJobResponse[] | undefined
      if (data?.some((j) => isInProgress(j.status))) {
        return 5000
      }
      return false
    },
  })

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Export History</h1>

      {isLoading && <p className="text-sm text-gray-500">Loading…</p>}

      {!isLoading && jobs.length === 0 && <p className="text-sm text-gray-500">No exports yet.</p>}

      {jobs.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Type</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Date Range</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Generated By</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Generated At</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Download</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const isExecutor =
                  job.export_type === "pdf_executor" || job.export_type === "excel_executor"
                const params = job.parameters as {
                  from_date?: string
                  to_date?: string
                }
                return (
                  <tr key={job.id} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span className="rounded-full bg-indigo-100 text-indigo-700 px-2 py-0.5 text-xs font-medium">
                          {TYPE_LABELS[job.export_type]}
                        </span>
                        {isExecutor && <span title="Full executor report">🔒</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {params.from_date && params.to_date
                        ? `${params.from_date} – ${params.to_date}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                      {shortId(job.generated_by)}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{formatDate(job.created_at)}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[job.status]}`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {job.status === "complete" && <DownloadButton job={job} />}
                      {isInProgress(job.status) && (
                        <span className="text-xs text-gray-400">Generating…</span>
                      )}
                      {job.status === "failed" && (
                        <span className="text-xs text-red-500" title={job.error_message ?? ""}>
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
