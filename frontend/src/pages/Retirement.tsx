// Tax-advantaged accounts grouped by tax treatment:
// - Tax-deferred: 401k, 403b, IRA
// - Tax-free: Roth IRA, HSA
// - Guaranteed: pension

import { useMemo } from "react"
import { useQuery, useQueries } from "@tanstack/react-query"
import { accountsApi } from "@/api/accounts"
import { snapshotsApi } from "@/api/snapshots"
import { ACCOUNT_LABELS } from "@/lib/accountLabels"
import { formatCurrency, formatMaskedAccountNumber } from "@/lib/formatters"
import type { AccountResponse, AccountType } from "@/api/types"

const GOLD = "#d9b96a"

// Tax treatment groupings
const TAX_DEFERRED: AccountType[] = ["retirement_401k", "retirement_403b", "retirement_ira"]
const TAX_FREE: AccountType[] = ["retirement_roth_ira", "hsa"]
const GUARANTEED: AccountType[] = ["pension"]

type TaxGroup = "Tax-deferred" | "Tax-free" | "Guaranteed"

const GROUP_DESCRIPTIONS: Record<TaxGroup, string> = {
  "Tax-deferred": "Contributions reduce taxable income now; taxed on withdrawal",
  "Tax-free": "Contributions from after-tax income; qualified withdrawals are tax-free",
  Guaranteed: "Defined benefit — employer bears the investment risk",
}

// ── Balance change from 2 most recent snapshots ───────────────────────────────

function useBalanceChange(accountId: string): string | null {
  const { data: snapshots } = useQuery({
    queryKey: ["snapshots", accountId],
    queryFn: () => snapshotsApi.list(accountId),
    staleTime: 60_000,
  })
  return useMemo(() => {
    if (!snapshots || snapshots.length < 2) return null
    const sorted = [...snapshots].sort(
      (a, b) => new Date(b.snapshot_date).getTime() - new Date(a.snapshot_date).getTime(),
    )
    const latest = Number(sorted[0].balance)
    const prev = Number(sorted[1].balance)
    if (prev === 0) return null
    const pct = ((latest - prev) / Math.abs(prev)) * 100
    return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`
  }, [snapshots])
}

// ── Account row ───────────────────────────────────────────────────────────────

function RetirementRow({ account }: { account: AccountResponse }) {
  const change = useBalanceChange(account.id)

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "12px",
        padding: "10px 16px",
        borderBottom: "1px solid var(--bd)",
      }}
    >
      <div style={{ minWidth: 0, flex: 1 }}>
        <div
          style={{
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--text2)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {account.nickname}
        </div>
        <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "1px" }}>
          {[
            account.institution_name,
            ACCOUNT_LABELS[account.account_type],
            formatMaskedAccountNumber(account.account_number_last4),
          ]
            .filter(Boolean)
            .join(" · ")}
        </div>
      </div>
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text2)" }}>
          {account.current_balance !== null ? formatCurrency(account.current_balance) : "—"}
        </div>
        {change !== null && (
          <div
            style={{
              fontSize: "10px",
              color: change.startsWith("+") ? "var(--up)" : "var(--liab)",
              marginTop: "1px",
            }}
          >
            {change}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Tax group section ─────────────────────────────────────────────────────────

function TaxGroupSection({ name, accounts }: { name: TaxGroup; accounts: AccountResponse[] }) {
  if (accounts.length === 0) return null
  const subtotal = accounts.reduce((s, a) => s + Number(a.current_balance ?? 0), 0)

  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--bd)",
        borderRadius: "14px",
        overflow: "hidden",
        marginBottom: "14px",
      }}
    >
      {/* Section header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <div>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text3)" }}>{name}</div>
          <div style={{ fontSize: "10px", color: "var(--muted)", marginTop: "2px" }}>
            {GROUP_DESCRIPTIONS[name]}
          </div>
        </div>
        <div style={{ fontSize: "14px", fontWeight: 700, color: GOLD, flexShrink: 0 }}>
          {formatCurrency(String(subtotal))}
        </div>
      </div>
      {/* Account rows */}
      <div>
        {accounts.map((a) => (
          <RetirementRow key={a.id} account={a} />
        ))}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Retirement() {
  const {
    data: accounts,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
    staleTime: 60_000,
  })

  // Prefetch snapshots for retirement accounts only so RetirementRow hits cache, not the network
  const RETIREMENT_TYPES = [...TAX_DEFERRED, ...TAX_FREE, ...GUARANTEED]
  useQueries({
    queries: (accounts ?? [])
      .filter((a) => RETIREMENT_TYPES.includes(a.account_type))
      .map((account) => ({
        queryKey: ["snapshots", account.id],
        queryFn: () => snapshotsApi.list(account.id),
        staleTime: 60_000,
      })),
  })

  const taxDeferred = useMemo(
    () => (accounts ?? []).filter((a) => TAX_DEFERRED.includes(a.account_type)),
    [accounts],
  )
  const taxFree = useMemo(
    () => (accounts ?? []).filter((a) => TAX_FREE.includes(a.account_type)),
    [accounts],
  )
  const guaranteed = useMemo(
    () => (accounts ?? []).filter((a) => GUARANTEED.includes(a.account_type)),
    [accounts],
  )

  const totalRetirement = useMemo(
    () =>
      [...taxDeferred, ...taxFree, ...guaranteed].reduce(
        (s, a) => s + Number(a.current_balance ?? 0),
        0,
      ),
    [taxDeferred, taxFree, guaranteed],
  )
  const totalTaxDeferred = useMemo(
    () => taxDeferred.reduce((s, a) => s + Number(a.current_balance ?? 0), 0),
    [taxDeferred],
  )
  const totalTaxFree = useMemo(
    () => taxFree.reduce((s, a) => s + Number(a.current_balance ?? 0), 0),
    [taxFree],
  )

  const hasAny = taxDeferred.length > 0 || taxFree.length > 0 || guaranteed.length > 0

  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "200px",
          color: "var(--muted)",
        }}
      >
        Loading…
      </div>
    )
  }
  if (error) {
    return <div style={{ padding: "32px", color: "var(--liab)" }}>Failed to load accounts.</div>
  }

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Retirement
        </h1>
      </div>

      {/* KPI row */}
      {hasAny && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "12px",
            marginBottom: "20px",
          }}
        >
          <div
            style={{
              background: "var(--grad)",
              border: "1px solid var(--accent-bd)",
              borderRadius: "14px",
              padding: "16px 18px",
              gridColumn: "span 3",
              display: "flex",
              alignItems: "center",
              gap: "32px",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "10px",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--label)",
                  marginBottom: "4px",
                }}
              >
                Total retirement
              </div>
              <div
                style={{ fontSize: "28px", fontWeight: 700, color: "var(--text)", lineHeight: 1 }}
              >
                {formatCurrency(String(totalRetirement))}
              </div>
            </div>
            {taxDeferred.length > 0 && (
              <div>
                <div style={{ fontSize: "10px", color: "var(--label)", marginBottom: "2px" }}>
                  Tax-deferred
                </div>
                <div style={{ fontSize: "15px", fontWeight: 600, color: GOLD }}>
                  {formatCurrency(String(totalTaxDeferred))}
                </div>
              </div>
            )}
            {taxFree.length > 0 && (
              <div>
                <div style={{ fontSize: "10px", color: "var(--label)", marginBottom: "2px" }}>
                  Tax-free
                </div>
                <div style={{ fontSize: "15px", fontWeight: 600, color: "var(--up)" }}>
                  {formatCurrency(String(totalTaxFree))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tax group sections */}
      {hasAny ? (
        <>
          <TaxGroupSection name="Tax-deferred" accounts={taxDeferred} />
          <TaxGroupSection name="Tax-free" accounts={taxFree} />
          <TaxGroupSection name="Guaranteed" accounts={guaranteed} />
        </>
      ) : (
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--bd)",
            borderRadius: "14px",
            padding: "48px 20px",
            textAlign: "center",
            color: "var(--muted)",
            fontSize: "13px",
          }}
        >
          No retirement accounts yet. Add a 401k, IRA, Roth IRA, HSA, or pension to get started.
        </div>
      )}
    </div>
  )
}
