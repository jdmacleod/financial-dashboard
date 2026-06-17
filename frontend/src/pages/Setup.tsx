import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { authApi } from "@/api/auth"
import { useAuth } from "@/hooks/useAuth"

const steps = ["Household", "Primary member", "Login credentials"]

const schema = z.object({
  household_name: z.string().min(1, "Required"),
  member_name: z.string().min(1, "Required"),
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "Minimum 8 characters"),
})

type FormValues = z.infer<typeof schema>

export default function Setup() {
  const navigate = useNavigate()
  const restoreToken = useAuth((s) => s.restoreToken)
  const [step, setStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    trigger,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function nextStep() {
    const fieldsPerStep: (keyof FormValues)[][] = [
      ["household_name"],
      ["member_name"],
      ["email", "password"],
    ]
    const valid = await trigger(fieldsPerStep[step])
    if (valid) setStep((s) => s + 1)
  }

  async function onSubmit(values: FormValues) {
    setError(null)
    try {
      const res = await authApi.setup(values)
      restoreToken(res.access_token)
      sessionStorage.setItem("access_token", res.access_token)
      navigate({ to: "/" })
    } catch {
      setError("Setup failed. Please try again.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Welcome to HearthLedger</h1>
        <p className="text-sm text-gray-500 mb-6">Let's set up your household in three steps.</p>

        {/* Step indicators */}
        <div className="flex gap-2 mb-8">
          {steps.map((label, i) => (
            <div key={label} className="flex-1">
              <div className={`h-1 rounded-full ${i <= step ? "bg-indigo-600" : "bg-gray-200"}`} />
              <p
                className={`mt-1 text-xs ${i === step ? "text-indigo-600 font-medium" : "text-gray-400"}`}
              >
                {label}
              </p>
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {step === 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Household name</label>
              <input
                {...register("household_name")}
                placeholder="e.g. The Smith Family"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {errors.household_name && (
                <p className="mt-1 text-xs text-red-600">{errors.household_name.message}</p>
              )}
            </div>
          )}

          {step === 1 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Your name</label>
              <input
                {...register("member_name")}
                placeholder="e.g. Alex Smith"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {errors.member_name && (
                <p className="mt-1 text-xs text-red-600">{errors.member_name.message}</p>
              )}
            </div>
          )}

          {step === 2 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  {...register("email")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                {errors.email && (
                  <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  {...register("password")}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                {errors.password && (
                  <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
                )}
              </div>
            </>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Back
              </button>
            )}
            {step < 2 ? (
              <button
                type="button"
                onClick={nextStep}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60 transition-colors"
              >
                {isSubmitting ? "Setting up…" : "Finish setup"}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
