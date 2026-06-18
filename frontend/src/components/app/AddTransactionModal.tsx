import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { transactionsApi } from "@/api/transactions"
import { transactionSchema, type TransactionFormValues } from "@/lib/transactionSchema"
import { handleTransactionMutationError } from "@/lib/errorHandlers"
import { RETIREMENT_ACCOUNT_TYPES } from "@/lib/accountTypes"
import { TransactionForm } from "./TransactionForm"
import type { AccountType, CategoryResponse } from "@/api/types"

function defaultCategoryId(
  accountType: AccountType,
  categories: CategoryResponse[],
): string | null {
  if (RETIREMENT_ACCOUNT_TYPES.includes(accountType)) {
    return categories.find((c) => c.name.toLowerCase() === "contributions")?.id ?? null
  }
  if (accountType === "pension") {
    return categories.find((c) => c.name.toLowerCase() === "income")?.id ?? null
  }
  return null
}

export function AddTransactionModal({
  accountId,
  accountType,
  categories,
  onClose,
}: {
  accountId: string
  accountType: AccountType
  categories: CategoryResponse[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const today = new Date().toISOString().slice(0, 10)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TransactionFormValues>({
    resolver: zodResolver(transactionSchema),
    defaultValues: {
      transaction_date: today,
      amount: "",
      payee_normalized: "",
      memo: "",
      category_id: defaultCategoryId(accountType, categories) ?? "",
    },
  })

  const create = useMutation({
    mutationFn: (values: TransactionFormValues) =>
      transactionsApi.create(accountId, {
        transaction_date: values.transaction_date,
        amount: values.amount,
        payee_normalized: values.payee_normalized,
        memo: values.memo || undefined,
        category_id: values.category_id || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", accountId] })
      onClose()
    },
    onError: (err) => handleTransactionMutationError(err, setError),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">New transaction</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <TransactionForm
          register={register}
          errors={errors}
          categories={categories}
          onSubmit={handleSubmit((v) => create.mutate(v))}
          onCancel={onClose}
          isPending={create.isPending}
          submitLabel="Add transaction"
          error={error}
        />
      </div>
    </div>
  )
}
