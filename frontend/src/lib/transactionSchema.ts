import { z } from "zod"

export const transactionSchema = z.object({
  transaction_date: z
    .string()
    .min(1, "Date is required")
    .refine((v) => !isNaN(Date.parse(v)), "Must be a valid date"),
  amount: z
    .string()
    .min(1, "Amount is required")
    .refine((v) => !isNaN(parseFloat(v)), "Must be a valid number")
    .refine((v) => parseFloat(v) !== 0, "Amount cannot be zero"),
  payee_normalized: z
    .string()
    .min(1, "Payee is required")
    .max(200, "Payee must be 200 characters or fewer"),
  memo: z.string().max(500, "Memo must be 500 characters or fewer").optional(),
  category_id: z.string().nullable().optional(),
})

export type TransactionFormValues = z.infer<typeof transactionSchema>
