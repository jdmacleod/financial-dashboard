import { useEffect, useRef, useState, type ChangeEvent } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { importsApi } from "@/api/imports"
import { ApiError } from "@/api/client"
import type { ImportJobResponse } from "@/api/types"

type Step = "pick" | "mapping" | "confirm" | "progress"

const MAPPING_FIELDS: { key: string; label: string }[] = [
  { key: "payee_raw", label: "Payee / description" },
  { key: "memo", label: "Memo" },
  { key: "post_date", label: "Post date" },
  { key: "external_id", label: "Reference / ID" },
]

const NONE = ""

export function ImportModal({ accountId, onClose }: { accountId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    dialogRef.current?.showModal()
  }, [])
  const [step, setStep] = useState<Step>("pick")
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [headers, setHeaders] = useState<string[]>([])
  const [previewRows, setPreviewRows] = useState<string[][]>([])
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [splitDebitCredit, setSplitDebitCredit] = useState(false)
  const [job, setJob] = useState<ImportJobResponse | null>(null)

  const isCsv = file?.name.toLowerCase().endsWith(".csv") ?? false

  const preview = useMutation({
    mutationFn: (f: File) => importsApi.preview(accountId, f),
    onSuccess: (res) => {
      setHeaders(res.headers)
      setPreviewRows(res.preview_rows)
      setMapping(res.suggested_mapping)
      setSplitDebitCredit(
        !res.suggested_mapping.amount &&
          Boolean(res.suggested_mapping.debit_amount || res.suggested_mapping.credit_amount),
      )
      setStep("mapping")
    },
    onError: () => setError("Could not read that file. Check it's a valid CSV."),
  })

  const start = useMutation({
    mutationFn: () => importsApi.start(accountId, file!, isCsv ? mapping : undefined),
    onSuccess: (res) => {
      setJob(res)
      setStep("progress")
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : "Failed to start import.")
    },
  })

  useEffect(() => {
    if (step !== "progress" || !job || job.status === "complete" || job.status === "failed") {
      return
    }
    const timer = setTimeout(async () => {
      const updated = await importsApi.getJob(job.id)
      setJob(updated)
      if (updated.status === "complete") {
        queryClient.invalidateQueries({ queryKey: ["transactions", accountId] })
      }
    }, 2000)
    return () => clearTimeout(timer)
  }, [step, job, accountId, queryClient])

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f) return
    setError(null)
    setFile(f)
    if (f.name.toLowerCase().endsWith(".csv")) {
      preview.mutate(f)
    } else {
      setStep("confirm")
    }
  }

  function updateMapping(field: string, header: string) {
    setMapping((prev) => {
      const next = { ...prev }
      if (header === NONE) {
        delete next[field]
      } else {
        next[field] = header
      }
      return next
    })
  }

  const mappingValid = splitDebitCredit
    ? Boolean(mapping.transaction_date && mapping.debit_amount && mapping.credit_amount)
    : Boolean(mapping.transaction_date && mapping.amount)

  return (
    <dialog
      ref={dialogRef}
      onCancel={onClose}
      aria-labelledby="import-transactions-title"
      className="w-full max-w-lg rounded-xl shadow-xl p-6 m-auto backdrop:bg-black/30"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 id="import-transactions-title" className="text-lg font-semibold">
          Import transactions
        </h2>
        <button onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600">
          ✕
        </button>
      </div>

      {step === "pick" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Choose a CSV, OFX, or QFX file exported from your bank.
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full rounded-lg border-2 border-dashed border-gray-300 px-4 py-8 text-sm text-gray-500 hover:border-indigo-400 hover:text-indigo-600 transition-colors"
          >
            {preview.isPending ? "Reading file…" : "Click to choose a file"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.ofx,.qfx"
            onChange={handleFileChange}
            className="hidden"
          />
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>
      )}

      {step === "mapping" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Match the columns in <span className="font-medium">{file?.name}</span> to transaction
            fields.
          </p>

          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-xs">
              <thead className="bg-gray-50">
                <tr>
                  {headers.map((h) => (
                    <th key={h} className="px-2 py-1.5 text-left font-medium text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.slice(0, 3).map((row, i) => (
                  <tr key={i} className="border-t border-gray-100">
                    {row.map((cell, j) => (
                      <td key={j} className="px-2 py-1.5 text-gray-700 whitespace-nowrap">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
              <select
                value={mapping.transaction_date ?? NONE}
                onChange={(e) => updateMapping("transaction_date", e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value={NONE}>— select column —</option>
                {headers.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">Amount</label>
                <button
                  type="button"
                  onClick={() => setSplitDebitCredit((v) => !v)}
                  className="text-xs text-indigo-600 hover:text-indigo-700"
                >
                  {splitDebitCredit ? "Use single column" : "Use separate debit/credit columns"}
                </button>
              </div>
              {splitDebitCredit ? (
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={mapping.debit_amount ?? NONE}
                    onChange={(e) => updateMapping("debit_amount", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value={NONE}>Debit column</option>
                    {headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                  <select
                    value={mapping.credit_amount ?? NONE}
                    onChange={(e) => updateMapping("credit_amount", e.target.value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value={NONE}>Credit column</option>
                    {headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <select
                  value={mapping.amount ?? NONE}
                  onChange={(e) => updateMapping("amount", e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value={NONE}>— select column —</option>
                  {headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {MAPPING_FIELDS.map((f) => (
              <div key={f.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {f.label} <span className="text-gray-400">(optional)</span>
                </label>
                <select
                  value={mapping[f.key] ?? NONE}
                  onChange={(e) => updateMapping(f.key, e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value={NONE}>— none —</option>
                  {headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setStep("pick")}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep("confirm")}
              disabled={!mappingValid}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "confirm" && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Import transactions from <span className="font-medium">{file?.name}</span>?
          </p>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => setStep(isCsv ? "mapping" : "pick")}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => start.mutate()}
              disabled={start.isPending}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {start.isPending ? "Starting…" : "Start import"}
            </button>
          </div>
        </div>
      )}

      {step === "progress" && job && (
        <div className="space-y-4">
          {(job.status === "pending" || job.status === "processing") && (
            <p className="text-sm text-gray-600">Importing transactions…</p>
          )}
          {job.status === "complete" && (
            <p className="text-sm text-gray-700">
              Imported {job.records_imported ?? 0} transaction
              {job.records_imported === 1 ? "" : "s"}.{" "}
              {job.records_skipped ? `${job.records_skipped} duplicates skipped.` : ""}
            </p>
          )}
          {job.status === "failed" && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {job.error_message ?? "Import failed."}
            </p>
          )}
          <button
            onClick={onClose}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            {job.status === "complete" || job.status === "failed" ? "Done" : "Close"}
          </button>
        </div>
      )}
    </dialog>
  )
}
