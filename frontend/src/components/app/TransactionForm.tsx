import type { FieldErrors, UseFormRegister } from "react-hook-form"
import type { TransactionFormValues } from "@/lib/transactionSchema"
import type { CategoryResponse } from "@/api/types"

interface TransactionFormProps {
  register: UseFormRegister<TransactionFormValues>
  errors: FieldErrors<TransactionFormValues>
  categories: CategoryResponse[]
  onSubmit: (e: React.FormEvent) => void
  onCancel: () => void
  isPending: boolean
  submitLabel: string
  error: string | null
}

export function TransactionForm({
  register,
  errors,
  categories,
  onSubmit,
  onCancel,
  isPending,
  submitLabel,
  error,
}: TransactionFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="transaction_date" className="block text-sm font-medium text-gray-700 mb-1">
          Date
        </label>
        <input
          id="transaction_date"
          type="date"
          {...register("transaction_date")}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.transaction_date && (
          <p className="mt-1 text-xs text-red-600">{errors.transaction_date.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1">
          Amount
          <span className="ml-1 text-xs font-normal text-gray-400">
            (negative for expenses, e.g. -50.00)
          </span>
        </label>
        <input
          id="amount"
          type="text"
          inputMode="decimal"
          {...register("amount")}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.amount && <p className="mt-1 text-xs text-red-600">{errors.amount.message}</p>}
      </div>

      <div>
        <label htmlFor="payee_normalized" className="block text-sm font-medium text-gray-700 mb-1">
          Payee
        </label>
        <input
          id="payee_normalized"
          type="text"
          {...register("payee_normalized")}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.payee_normalized && (
          <p className="mt-1 text-xs text-red-600">{errors.payee_normalized.message}</p>
        )}
      </div>

      <div>
        <label htmlFor="memo" className="block text-sm font-medium text-gray-700 mb-1">
          Memo <span className="text-gray-400">(optional)</span>
        </label>
        <input
          id="memo"
          type="text"
          {...register("memo")}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {errors.memo && <p className="mt-1 text-xs text-red-600">{errors.memo.message}</p>}
      </div>

      <div>
        <label htmlFor="category_id" className="block text-sm font-medium text-gray-700 mb-1">
          Category <span className="text-gray-400">(optional)</span>
        </label>
        <select
          id="category_id"
          {...register("category_id")}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Uncategorized</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}

      <div className="flex gap-3 pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          {isPending ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  )
}
