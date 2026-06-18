import { ApiError } from "@/api/client"

export function handleTransactionMutationError(
  err: unknown,
  setError: (msg: string) => void,
  extraCodes: Record<number, string> = {},
) {
  if (err instanceof ApiError) {
    if (extraCodes[err.status]) {
      setError(extraCodes[err.status])
    } else if (err.status === 403) {
      setError("Not authorized to modify this account.")
    } else if (err.status === 422) {
      setError(typeof err.detail === "string" ? err.detail : "Validation error. Check your inputs.")
    } else {
      setError("Failed to save. Please try again.")
    }
  } else {
    setError("Failed to save. Please try again.")
  }
}
