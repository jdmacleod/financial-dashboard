import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { transactionsApi } from "@/api/transactions"
import { transactionSchema, type TransactionFormValues } from "@/lib/transactionSchema"
import { handleTransactionMutationError } from "@/lib/errorHandlers"
import { TransactionForm } from "./TransactionForm"
import type { CategoryResponse, TransactionResponse } from "@/api/types"

export function EditTransactionModal({
  transaction,
  categories,
  onClose,
}: {
  transaction: TransactionResponse
  categories: CategoryResponse[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionSchema),
    defaultValues: {
      transaction_date: transaction.transaction_date,
      amount: transaction.amount,
      payee_normalized: transaction.payee_normalized ?? transaction.payee_raw ?? "",
      memo: transaction.memo ?? "",
      category_id: transaction.category_id ?? "",
    },
  })

  const update = useMutation({
    mutationFn: (values: TransactionFormValues) =>
      transactionsApi.update(transaction.id, {
        transaction_date: values.transaction_date,
        amount: values.amount,
        payee_normalized: values.payee_normalized,
        memo: values.memo || null,
        category_id: values.category_id || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", transaction.account_id] })
      onClose()
    },
    onError: (err) =>
      handleTransactionMutationError(err, setError, {
        404: "Transaction no longer exists.",
      }),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Edit transaction</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <TransactionForm
          register={register}
          errors={errors}
          categories={categories}
          onSubmit={handleSubmit((v) => update.mutate(v))}
          onCancel={onClose}
          isPending={update.isPending}
          submitLabel="Save changes"
          error={error}
        />
      </div>
    </div>
  )
}
