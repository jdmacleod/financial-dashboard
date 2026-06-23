import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { ApiError } from "@/api/client"
import { authApi } from "@/api/auth"
import { useAuth } from "@/hooks/useAuth"

const schema = z
  .object({
    current_password: z.string().min(1, "Enter the temporary password you were given"),
    new_password: z.string().min(8, "At least 8 characters"),
    confirm: z.string().min(1, "Re-enter the new password"),
  })
  .refine((d) => d.new_password === d.confirm, {
    path: ["confirm"],
    message: "Passwords don't match",
  })
type FormValues = z.infer<typeof schema>

const inputClass =
  "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"

/**
 * Forced first-login password reset. Rendered as a full-screen takeover by
 * AppLayout whenever the user's mustChangePassword flag is set — blocks all
 * app navigation until they replace the provisioned temporary password.
 */
export default function ForcedPasswordReset() {
  const navigate = useNavigate()
  const clearFlag = useAuth((s) => s.clearMustChangePassword)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      await authApi.changePassword(values.current_password, values.new_password)
      clearFlag()
      navigate({ to: "/" })
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setServerError("That temporary password is incorrect.")
      } else {
        setServerError("Could not set your password. Please try again.")
      }
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900">Set your password</h1>
        <p className="mt-1 text-sm text-gray-500">
          You signed in with a temporary password. Choose your own to continue.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-5 space-y-4">
          <div>
            <label htmlFor="fpr-current" className="mb-1 block text-sm font-medium text-gray-700">
              Temporary password
            </label>
            <input
              id="fpr-current"
              type="password"
              autoComplete="current-password"
              {...register("current_password")}
              className={inputClass}
            />
            {errors.current_password && (
              <p className="mt-1 text-xs text-red-600">{errors.current_password.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="fpr-new" className="mb-1 block text-sm font-medium text-gray-700">
              New password
            </label>
            <input
              id="fpr-new"
              type="password"
              autoComplete="new-password"
              {...register("new_password")}
              className={inputClass}
            />
            {errors.new_password ? (
              <p className="mt-1 text-xs text-red-600">{errors.new_password.message}</p>
            ) : (
              <p className="mt-1 text-xs text-gray-400">At least 8 characters.</p>
            )}
          </div>

          <div>
            <label htmlFor="fpr-confirm" className="mb-1 block text-sm font-medium text-gray-700">
              Confirm new password
            </label>
            <input
              id="fpr-confirm"
              type="password"
              autoComplete="new-password"
              {...register("confirm")}
              className={inputClass}
            />
            {errors.confirm && (
              <p className="mt-1 text-xs text-red-600">{errors.confirm.message}</p>
            )}
          </div>

          {serverError && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {isSubmitting ? "Setting…" : "Set password"}
          </button>
        </form>
      </div>
    </div>
  )
}
