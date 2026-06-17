import { useEffect, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { authApi } from "@/api/auth"
import { exportApi } from "@/api/exports"
import { ApiError } from "@/api/client"
import { useAuth } from "@/hooks/useAuth"
import type { ExportJobResponse, ExportType } from "@/api/types"

type Step = "configure" | "reauth" | "generating"

interface FormatCard {
  type: ExportType
  title: string
  description: string
  executorOnly: boolean
}

const FORMAT_CARDS: FormatCard[] = [
  {
    type: "pdf_summary",
    title: "PDF Summary",
    description: "Anonymized report with account numbers masked",
    executorOnly: false,
  },
  {
    type: "pdf_executor",
    title: "PDF Full (Executor)",
    description: "Full report including complete account numbers",
    executorOnly: true,
  },
  {
    type: "excel_summary",
    title: "Excel Summary",
    description: "Spreadsheet with masked account data",
    executorOnly: false,
  },
  {
    type: "excel_executor",
    title: "Excel Full (Executor)",
    description: "Full spreadsheet including all account details",
    executorOnly: true,
  },
]

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function firstOfYearStr() {
  const y = new Date().getFullYear()
  return `${y}-01-01`
}

interface ExportModalInnerProps {
  onClose: () => void
}

function ExportModalInner({ onClose }: ExportModalInnerProps) {
  const isPrimary = useAuth((s) => s.role === "primary")

  const [step, setStep] = useState<Step>("configure")
  const [selectedType, setSelectedType] = useState<ExportType>("pdf_summary")
  const [fromDate, setFromDate] = useState(firstOfYearStr())
  const [toDate, setToDate] = useState(todayStr())
  const [reauthPassword, setReauthPassword] = useState("")
  const [reauthAttempts, setReauthAttempts] = useState(0)
  const [reauthError, setReauthError] = useState<string | null>(null)
  const [reauthToken, setReauthToken] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<ExportJobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isExecutor = selectedType === "pdf_executor" || selectedType === "excel_executor"

  // Poll for job status
  useEffect(() => {
    if (step !== "generating" || !jobId || !job) return
    if (job.status === "complete" || job.status === "failed") return

    const timer = setTimeout(async () => {
      try {
        const updated = await exportApi.get(jobId)
        setJob(updated)
      } catch {
        // ignore polling errors
      }
    }, 2000)
    return () => clearTimeout(timer)
  }, [step, jobId, job])

  const createExport = useMutation({
    mutationFn: (token: string | undefined) =>
      exportApi.create(
        {
          export_type: selectedType,
          from_date: fromDate,
          to_date: toDate,
        },
        token,
      ),
    onSuccess: async (res) => {
      setJobId(res.export_job_id)
      const initial = await exportApi.get(res.export_job_id)
      setJob(initial)
      setStep("generating")
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : "Failed to start export.")
    },
  })

  const doReauth = useMutation({
    mutationFn: () => authApi.reauth(reauthPassword),
    onSuccess: (res) => {
      setReauthToken(res.reauth_token)
      createExport.mutate(res.reauth_token)
    },
    onError: (err) => {
      const attempts = reauthAttempts + 1
      setReauthAttempts(attempts)
      setReauthError(err instanceof ApiError ? String(err.detail) : "Incorrect password.")
      if (attempts >= 3) {
        setReauthError("Too many failed attempts. Please close and try again.")
      }
    },
  })

  function handleGenerate() {
    setError(null)
    if (isExecutor) {
      setStep("reauth")
    } else {
      createExport.mutate(undefined)
      setStep("generating")
    }
  }

  function handleDownload() {
    if (!jobId || !job?.filename) return
    exportApi.download(jobId, reauthToken ?? undefined).then((blob) => {
      const ext = selectedType.startsWith("pdf") ? "pdf" : "xlsx"
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = job.filename ?? `hearthledger-export.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Export Report</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        {/* Step 1: Configure */}
        {step === "configure" && (
          <div className="space-y-5">
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Format</p>
              <div className="grid grid-cols-2 gap-3">
                {FORMAT_CARDS.map((card) => {
                  const disabled = card.executorOnly && !isPrimary
                  const selected = selectedType === card.type
                  return (
                    <button
                      key={card.type}
                      disabled={disabled}
                      onClick={() => !disabled && setSelectedType(card.type)}
                      className={[
                        "rounded-lg border-2 p-3 text-left transition-colors",
                        selected
                          ? "border-indigo-600 bg-indigo-50"
                          : "border-gray-200 hover:border-indigo-300",
                        disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer",
                      ].join(" ")}
                    >
                      <div className="text-sm font-medium text-gray-900">{card.title}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{card.description}</div>
                      {card.executorOnly && (
                        <div className="text-xs text-indigo-600 mt-1">Primary members only</div>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">From date</label>
                <input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">To date</label>
                <input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleGenerate}
                disabled={createExport.isPending}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                Generate
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Re-authenticate */}
        {step === "reauth" && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Executor reports contain full account numbers and sensitive financial data. Please
              confirm your password to continue.
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password"
                value={reauthPassword}
                onChange={(e) => setReauthPassword(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" &&
                  !doReauth.isPending &&
                  reauthAttempts < 3 &&
                  doReauth.mutate()
                }
                placeholder="Enter your password"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            {reauthError && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {reauthError}
                {reauthAttempts < 3 &&
                  ` (${3 - reauthAttempts} attempt${3 - reauthAttempts === 1 ? "" : "s"} remaining)`}
              </p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => setStep("configure")}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={() => doReauth.mutate()}
                disabled={doReauth.isPending || reauthAttempts >= 3 || !reauthPassword}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                {doReauth.isPending ? "Verifying…" : "Confirm"}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Generating */}
        {step === "generating" && (
          <div className="space-y-4">
            {(!job || job.status === "pending" || job.status === "processing") && (
              <div className="flex flex-col items-center py-6 gap-3">
                <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-gray-600">Generating your report…</p>
              </div>
            )}
            {job?.status === "complete" && (
              <div className="space-y-4">
                <p className="text-sm text-gray-700 font-medium">Your report is ready!</p>
                <button
                  onClick={handleDownload}
                  className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Download
                </button>
              </div>
            )}
            {job?.status === "failed" && (
              <div className="space-y-4">
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                  {job.error_message ?? "Export failed. Please try again."}
                </p>
                <button
                  onClick={() => setStep("configure")}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Retry
                </button>
              </div>
            )}
            {job?.status === "complete" || job?.status === "failed" ? (
              <button
                onClick={onClose}
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}

export function ExportModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null
  return <ExportModalInner onClose={onClose} />
}
