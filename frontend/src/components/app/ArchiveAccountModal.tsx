import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { accountsApi } from "@/api/accounts"
import { ACCOUNT_LABELS } from "@/lib/accountLabels"
import type { AccountResponse } from "@/api/types"

interface ArchiveAccountModalProps {
  account: AccountResponse
  onClose: () => void
}

export default function ArchiveAccountModal({ account, onClose }: ArchiveAccountModalProps) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const archive = useMutation({
    mutationFn: () => accountsApi.deactivate(account.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      onClose()
    },
    onError: () => setError("Failed to archive account. You may not have permission."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Archive account?</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <div className="mb-5">
          <p className="text-sm font-medium text-gray-900 mb-1">{account.nickname}</p>
          <p className="text-xs text-gray-500 mb-4">{ACCOUNT_LABELS[account.account_type]}</p>
          <p className="text-sm text-gray-700">
            This hides the account from all views. Your transaction history and balance snapshots
            are preserved and will still appear in historical reports.
          </p>
        </div>

        {error && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            autoFocus
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => archive.mutate()}
            disabled={archive.isPending}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
          >
            {archive.isPending ? "Archiving…" : "Archive account"}
          </button>
        </div>
      </div>
    </div>
  )
}
