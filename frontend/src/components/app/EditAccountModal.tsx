import { useEffect, useRef } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { accountsApi } from "@/api/accounts"
import { useAuth } from "@/hooks/useAuth"
import { useOwnershipEntities } from "@/hooks/useOwnershipEntities"
import type { AccountResponse } from "@/api/types"

const editSchema = z.object({
  nickname: z.string().min(1, "Required"),
  institution_name: z.string().optional(),
  account_number: z.string().optional(),
  notes: z.string().optional(),
  include_in_net_worth: z.boolean(),
  ownership_entity_id: z.string().nullable(),
  // "" = unclassified (NULL); otherwise pretax | roth | taxable.
  tax_treatment: z.enum(["", "pretax", "roth", "taxable"]),
})
type EditForm = z.infer<typeof editSchema>

interface EditAccountModalProps {
  account: AccountResponse
  onClose: () => void
}

const INPUT_STYLE: React.CSSProperties = {
  width: "100%",
  borderRadius: "9px",
  border: "1px solid var(--bd2)",
  background: "var(--bg)",
  color: "var(--text)",
  padding: "9px 12px",
  fontSize: "14px",
  outline: "none",
  boxSizing: "border-box",
}

const LABEL_STYLE: React.CSSProperties = {
  display: "block",
  fontSize: "12px",
  fontWeight: 500,
  color: "var(--text3)",
  marginBottom: "6px",
}

export default function EditAccountModal({ account, onClose }: EditAccountModalProps) {
  const qc = useQueryClient()
  const overlayRef = useRef<HTMLDivElement>(null)
  const role = useAuth((s) => s.role)
  const canViewAccountNumber = role === "primary" || role === "partner"
  const { data: entities } = useOwnershipEntities()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EditForm>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      nickname: account.nickname,
      institution_name: account.institution_name ?? "",
      account_number: "",
      notes: account.notes ?? "",
      include_in_net_worth: account.include_in_net_worth,
      ownership_entity_id: account.ownership_entity_id,
      tax_treatment: account.tax_treatment ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: EditForm) =>
      accountsApi.update(account.id, {
        nickname: data.nickname,
        institution_name: data.institution_name || null,
        account_number: data.account_number || null,
        notes: data.notes || null,
        include_in_net_worth: data.include_in_net_worth,
        ownership_entity_id: data.ownership_entity_id || null,
        tax_treatment: data.tax_treatment || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] })
      onClose()
    },
  })

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose])

  function onOverlayClick(e: React.MouseEvent) {
    if (e.target === overlayRef.current) onClose()
  }

  return (
    <div
      ref={overlayRef}
      onClick={onOverlayClick}
      data-testid="modal-overlay"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <div
        style={{
          background: "var(--card)",
          border: "1px solid var(--bd)",
          borderRadius: "16px",
          padding: "28px 28px 24px",
          width: "100%",
          maxWidth: "420px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "22px",
          }}
        >
          <h2 style={{ fontSize: "17px", fontWeight: 700, color: "var(--text)", margin: 0 }}>
            Edit account
          </h2>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--muted)",
              fontSize: "20px",
              lineHeight: 1,
              padding: "2px 6px",
            }}
          >
            ×
          </button>
        </div>

        <form
          onSubmit={handleSubmit((data) => mutation.mutate(data))}
          style={{ display: "flex", flexDirection: "column", gap: "16px" }}
        >
          {/* Nickname */}
          <div>
            <label style={LABEL_STYLE}>Account name</label>
            <input
              {...register("nickname")}
              style={INPUT_STYLE}
              placeholder="e.g. Chase Checking"
            />
            {errors.nickname && (
              <p style={{ marginTop: "4px", fontSize: "11px", color: "var(--liab)" }}>
                {errors.nickname.message}
              </p>
            )}
          </div>

          {/* Institution */}
          <div>
            <label style={LABEL_STYLE}>Institution</label>
            <input
              {...register("institution_name")}
              style={INPUT_STYLE}
              placeholder="e.g. Chase Bank"
            />
          </div>

          {/* Titling entity */}
          {entities && entities.length > 0 && (
            <div>
              <label style={LABEL_STYLE}>Titled to</label>
              <select {...register("ownership_entity_id")} style={INPUT_STYLE}>
                <option value="">Directly owned</option>
                {entities.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Tax treatment — drives RMD eligibility (pretax only) */}
          <div>
            <label htmlFor="edit-tax-treatment" style={LABEL_STYLE}>
              Tax treatment
            </label>
            <select id="edit-tax-treatment" {...register("tax_treatment")} style={INPUT_STYLE}>
              <option value="">Not set</option>
              <option value="pretax">Pre-tax (traditional)</option>
              <option value="roth">Roth (after-tax)</option>
              <option value="taxable">Taxable</option>
            </select>
            <p style={{ marginTop: "4px", fontSize: "11px", color: "var(--label)" }}>
              Pre-tax retirement balances drive required minimum distributions.
            </p>
          </div>

          {/* Account number — only shown to primary/partner */}
          {canViewAccountNumber && (
            <div>
              <label style={LABEL_STYLE}>Account number</label>
              <input
                {...register("account_number")}
                style={INPUT_STYLE}
                placeholder={
                  account.account_number_last4
                    ? `•••• ${account.account_number_last4} — enter to replace`
                    : "Optional"
                }
                autoComplete="off"
              />
            </div>
          )}

          {/* Notes */}
          <div>
            <label style={LABEL_STYLE}>Notes</label>
            <textarea
              {...register("notes")}
              rows={3}
              style={{ ...INPUT_STYLE, resize: "vertical", fontFamily: "inherit" }}
              placeholder="Optional notes about this account"
            />
          </div>

          {/* Include in net worth */}
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              cursor: "pointer",
              fontSize: "13px",
              color: "var(--text3)",
            }}
          >
            <input type="checkbox" {...register("include_in_net_worth")} />
            Include in net worth
          </label>

          {mutation.isError && (
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
              Failed to save. Please try again.
            </div>
          )}

          <div
            style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "4px" }}
          >
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "9px 18px",
                borderRadius: "9px",
                border: "1px solid var(--bd2)",
                background: "transparent",
                color: "var(--text3)",
                fontSize: "14px",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || mutation.isPending}
              style={{
                padding: "9px 18px",
                borderRadius: "9px",
                border: "none",
                background: "var(--toggle-on-bg)",
                color: "var(--toggle-on-text)",
                fontSize: "14px",
                fontWeight: 600,
                cursor: isSubmitting || mutation.isPending ? "not-allowed" : "pointer",
                opacity: isSubmitting || mutation.isPending ? 0.65 : 1,
              }}
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
