import { useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { ApiError } from "@/api/client"
import { provisioningApi } from "@/api/provisioning"
import { useAuth } from "@/hooks/useAuth"
import type { ProvisionResponse } from "@/api/types"

const today = new Date().toISOString().slice(0, 10)

const schema = z.object({
  display_name: z.string().min(1, "Required"),
  role: z.enum(["primary", "partner", "dependent"]),
  email: z.string().min(3, "Required"),
  date_of_birth: z
    .string()
    .optional()
    .refine((v) => !v || v <= today, "Date of birth can't be in the future"),
})
type FormValues = z.infer<typeof schema>

const inputClass =
  "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"

/**
 * Provisions a login-capable member in one action (POST /members/provision) and
 * reveals the one-time temporary password the inviter must hand to the new
 * person. The success state treats that secret as the feature: copy button,
 * "shown once" warning, regenerate, and a confirm-before-close guard so it
 * can't be dismissed uncaptured.
 */
export function AddPersonSlideOver({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const viewerIsPrimary = useAuth((s) => s.role === "primary")
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ProvisionResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const {
    register,
    handleSubmit,
    setError: setFieldError,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: "partner" },
  })

  const provision = useMutation({
    mutationFn: (data: FormValues) =>
      provisioningApi.provision({ ...data, date_of_birth: data.date_of_birth || null }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["members"] })
      setResult(res)
      setError(null)
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 409) {
        setFieldError("email", { message: "That email already has a login." })
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Only a primary can add another primary.")
      } else {
        setError("Failed to add the person. Please try again.")
      }
    },
  })

  const regenerate = useMutation({
    mutationFn: () => provisioningApi.regenerateTemporaryPassword(result!.user.id),
    onSuccess: (res) => {
      setResult((prev) => (prev ? { ...prev, temporary_password: res.temporary_password } : prev))
      setCopied(false)
    },
  })

  async function copyPassword() {
    if (!result) return
    try {
      await navigator.clipboard.writeText(result.temporary_password)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  function guardedClose() {
    if (result) {
      const ok = window.confirm(
        "Make sure you've copied the temporary password — it won't be shown again. Close anyway?",
      )
      if (!ok) return
    }
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={guardedClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label={result ? "Person added" : "Add person"}
        className="flex w-full max-w-sm flex-col gap-4 bg-white p-6 shadow-xl"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{result ? "Person added" : "Add person"}</h2>
          <button
            onClick={guardedClose}
            aria-label="Close"
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        {!result ? (
          <form onSubmit={handleSubmit((d) => provision.mutate(d))} className="space-y-4">
            <div>
              <label htmlFor="ap-name" className="mb-1 block text-sm font-medium text-gray-700">
                Display name
              </label>
              <input
                id="ap-name"
                {...register("display_name")}
                placeholder="e.g. Jamie Smith"
                className={inputClass}
              />
              {errors.display_name && (
                <p className="mt-1 text-xs text-red-600">{errors.display_name.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="ap-email" className="mb-1 block text-sm font-medium text-gray-700">
                Email (their sign-in ID)
              </label>
              <input
                id="ap-email"
                {...register("email")}
                placeholder="jamie@example.com"
                className={inputClass}
              />
              {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>}
            </div>

            <div>
              <label htmlFor="ap-role" className="mb-1 block text-sm font-medium text-gray-700">
                Role
              </label>
              <select id="ap-role" {...register("role")} className={inputClass}>
                <option value="partner">Partner</option>
                <option value="dependent">Dependent</option>
                {/* Only a primary may add another primary (server enforces too). */}
                {viewerIsPrimary && <option value="primary">Primary</option>}
              </select>
            </div>

            <div>
              <label htmlFor="ap-dob" className="mb-1 block text-sm font-medium text-gray-700">
                Date of birth <span className="font-normal text-gray-400">(optional)</span>
              </label>
              <input
                id="ap-dob"
                type="date"
                max={today}
                {...register("date_of_birth")}
                className={inputClass}
              />
              {errors.date_of_birth && (
                <p className="mt-1 text-xs text-red-600">{errors.date_of_birth.message}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">
                Powers age-based projections like FIRE and required minimum distributions.
              </p>
            </div>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={provision.isPending}
              className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {provision.isPending ? "Adding…" : "Add person"}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-gray-700">
              <span className="font-medium">{result.member.display_name}</span> can now sign in with{" "}
              <span className="font-medium">{result.user.email}</span> and this temporary password:
            </p>

            <div>
              <TempPasswordField value={result.temporary_password} />
              <button
                onClick={copyPassword}
                className="mt-2 inline-flex min-h-[44px] w-full items-center justify-center rounded-lg border border-gray-300 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {copied ? "Copied ✓" : "Copy password"}
              </button>
              <span aria-live="polite" className="sr-only">
                {copied ? "Temporary password copied to clipboard." : ""}
              </span>
            </div>

            <p className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <span aria-hidden="true">⚠️</span>
              <span>
                Shown once. Give it to {result.member.display_name} now — they'll set their own
                password the first time they sign in.
              </span>
            </p>

            <button
              onClick={() => regenerate.mutate()}
              disabled={regenerate.isPending}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-700 disabled:opacity-60"
            >
              {regenerate.isPending ? "Regenerating…" : "Regenerate password"}
            </button>

            <button
              onClick={onClose}
              className="mt-2 w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              I've saved it — done
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function TempPasswordField({ value }: { value: string }) {
  const ref = useRef<HTMLInputElement>(null)
  return (
    <input
      ref={ref}
      readOnly
      autoFocus
      value={value}
      onFocus={(e) => e.currentTarget.select()}
      aria-label="Temporary password (one-time)"
      className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-base text-gray-900"
    />
  )
}
