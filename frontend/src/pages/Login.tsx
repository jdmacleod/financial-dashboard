import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useAuth } from "@/hooks/useAuth"
import { ApiError } from "@/api/client"

const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(1, "Password required"),
})

type FormValues = z.infer<typeof schema>

export default function Login() {
  const navigate = useNavigate()
  const login = useAuth((s) => s.login)
  const [serverError, setServerError] = useState<string | null>(null)
  const [lockoutMsg, setLockoutMsg] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    setServerError(null)
    setLockoutMsg(null)
    try {
      await login(values.email, values.password)
      navigate({ to: "/" })
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 423) {
          const detail = err.detail as { minutes_remaining?: number }
          const mins = detail?.minutes_remaining ?? "a few"
          setLockoutMsg(`Account locked. Try again in ${mins} minute${mins === 1 ? "" : "s"}.`)
        } else {
          setServerError("Invalid email or password.")
        }
      } else {
        setServerError("An unexpected error occurred.")
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">HearthLedger</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in to your household</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              autoComplete="email"
              {...register("email")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              autoComplete="current-password"
              {...register("password")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
            )}
          </div>

          {serverError && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {serverError}
            </p>
          )}
          {lockoutMsg && (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              {lockoutMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60 transition-colors"
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  )
}
