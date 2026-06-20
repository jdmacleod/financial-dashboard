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
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "360px",
          background: "var(--card)",
          border: "1px solid var(--bd)",
          borderRadius: "18px",
          padding: "36px 32px",
        }}
      >
        {/* Wordmark */}
        <div style={{ marginBottom: "24px" }}>
          <h1
            style={{
              fontSize: "20px",
              fontWeight: 700,
              color: "var(--text)",
              margin: 0,
              letterSpacing: "-0.01em",
            }}
          >
            HearthLedger
          </h1>
          <p style={{ fontSize: "13px", color: "var(--muted)", marginTop: "4px" }}>
            Sign in to your household
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          style={{ display: "flex", flexDirection: "column", gap: "16px" }}
        >
          {/* Email */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--text3)",
                marginBottom: "6px",
                letterSpacing: "0.01em",
              }}
            >
              Email
            </label>
            <input
              type="email"
              autoComplete="email"
              {...register("email")}
              style={{
                width: "100%",
                borderRadius: "9px",
                border: "1px solid var(--bd2)",
                background: "var(--bg)",
                color: "var(--text)",
                padding: "9px 12px",
                fontSize: "14px",
                outline: "none",
                boxSizing: "border-box",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "var(--toggle-on-bg)"
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(70,184,136,0.14)"
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "var(--bd2)"
                e.currentTarget.style.boxShadow = "none"
              }}
            />
            {errors.email && (
              <p style={{ marginTop: "4px", fontSize: "11px", color: "var(--liab)" }}>
                {errors.email.message}
              </p>
            )}
          </div>

          {/* Password */}
          <div>
            <label
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--text3)",
                marginBottom: "6px",
                letterSpacing: "0.01em",
              }}
            >
              Password
            </label>
            <input
              type="password"
              autoComplete="current-password"
              {...register("password")}
              style={{
                width: "100%",
                borderRadius: "9px",
                border: "1px solid var(--bd2)",
                background: "var(--bg)",
                color: "var(--text)",
                padding: "9px 12px",
                fontSize: "14px",
                outline: "none",
                boxSizing: "border-box",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "var(--toggle-on-bg)"
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(70,184,136,0.14)"
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "var(--bd2)"
                e.currentTarget.style.boxShadow = "none"
              }}
            />
            {errors.password && (
              <p style={{ marginTop: "4px", fontSize: "11px", color: "var(--liab)" }}>
                {errors.password.message}
              </p>
            )}
          </div>

          {/* Server errors */}
          {serverError && (
            <div
              style={{
                fontSize: "13px",
                color: "var(--liab)",
                background: "rgba(224,180,138,0.10)",
                border: "1px solid rgba(224,180,138,0.25)",
                borderRadius: "9px",
                padding: "10px 12px",
              }}
            >
              {serverError}
            </div>
          )}
          {lockoutMsg && (
            <div
              style={{
                fontSize: "13px",
                color: "var(--gold, #d9b96a)",
                background: "rgba(217,185,106,0.10)",
                border: "1px solid rgba(217,185,106,0.25)",
                borderRadius: "9px",
                padding: "10px 12px",
              }}
            >
              {lockoutMsg}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              width: "100%",
              borderRadius: "9px",
              background: "var(--toggle-on-bg)",
              color: "var(--toggle-on-text)",
              border: "none",
              padding: "10px 16px",
              fontSize: "14px",
              fontWeight: 600,
              cursor: isSubmitting ? "not-allowed" : "pointer",
              opacity: isSubmitting ? 0.65 : 1,
              transition: "opacity 0.15s",
            }}
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  )
}
