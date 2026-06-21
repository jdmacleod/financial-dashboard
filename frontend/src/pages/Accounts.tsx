import { useState, useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery, useQueries } from "@tanstack/react-query"
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { accountsApi } from "@/api/accounts"
import { snapshotsApi } from "@/api/snapshots"
import { useAuth } from "@/hooks/useAuth"
import { ACCOUNT_LABELS, ACCOUNT_CATEGORY_COLORS } from "@/lib/accountLabels"
import { RETIREMENT_ACCOUNT_TYPES, BROKERAGE_ACCOUNT_TYPES } from "@/lib/accountTypes"
import { formatCurrency, formatMaskedAccountNumber } from "@/lib/formatters"
import AddAccountModal from "@/components/app/AddAccountModal"
import ArchiveAccountModal from "@/components/app/ArchiveAccountModal"
import EditAccountModal from "@/components/app/EditAccountModal"
import type { AccountResponse, AccountType } from "@/api/types"

// ── Category definitions ──────────────────────────────────────────────────────

const BANKING_TYPES: AccountType[] = ["checking", "savings", "other_asset"]
const REAL_ESTATE_TYPES: AccountType[] = ["real_estate"]
const LIABILITY_TYPES: AccountType[] = [
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "student_loan",
  "other_liability",
  "heloc",
]

const ACCOUNTS_PAGE_TYPES: AccountType[] = [
  "checking",
  "savings",
  "other_asset",
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "student_loan",
  "other_liability",
  "heloc",
]

type CategoryName = "Banking & Cash" | "Retirement" | "Investments" | "Real estate" | "Liabilities"

function categorise(accounts: AccountResponse[]): Record<CategoryName, AccountResponse[]> {
  const result: Record<CategoryName, AccountResponse[]> = {
    "Banking & Cash": [],
    Retirement: [],
    Investments: [],
    "Real estate": [],
    Liabilities: [],
  }
  for (const a of accounts) {
    if (BANKING_TYPES.includes(a.account_type)) result["Banking & Cash"].push(a)
    else if (
      RETIREMENT_ACCOUNT_TYPES.includes(a.account_type) ||
      a.account_type === "hsa" ||
      a.account_type === "pension"
    )
      result.Retirement.push(a)
    else if (BROKERAGE_ACCOUNT_TYPES.includes(a.account_type)) result.Investments.push(a)
    else if (REAL_ESTATE_TYPES.includes(a.account_type)) result["Real estate"].push(a)
    else if (LIABILITY_TYPES.includes(a.account_type)) result.Liabilities.push(a)
  }
  return result
}

function groupSubtotal(accounts: AccountResponse[]): number {
  return accounts.reduce((s, a) => s + Number(a.current_balance ?? 0), 0)
}

// Balance change from 2 most recent snapshots
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

function AccountRow({
  account,
  category,
  selected,
  onSelect,
}: {
  account: AccountResponse
  category: CategoryName
  selected: boolean
  onSelect: () => void
}) {
  const change = useBalanceChange(account.id)
  const dot = ACCOUNT_CATEGORY_COLORS[category] ?? "var(--muted)"
  const isLiability = LIABILITY_TYPES.includes(account.account_type)

  return (
    <button
      onClick={onSelect}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "10px 14px",
        width: "100%",
        textAlign: "left",
        background: selected ? "var(--row-active)" : "transparent",
        border: "none",
        cursor: "pointer",
        borderRadius: "8px",
      }}
    >
      {/* Color dot */}
      <span
        style={{
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          background: dot,
          flexShrink: 0,
        }}
      />
      {/* Name + institution */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: "13px",
            fontWeight: 500,
            color: "var(--text3)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {account.nickname}
        </div>
        <div style={{ fontSize: "11px", color: "var(--muted)" }}>
          {[
            account.institution_name,
            ACCOUNT_LABELS[account.account_type],
            formatMaskedAccountNumber(account.account_number_last4),
          ]
            .filter(Boolean)
            .join(" · ")}
        </div>
      </div>
      {/* Balance */}
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <div
          style={{
            fontSize: "13px",
            fontWeight: 600,
            color: isLiability ? "var(--liab)" : "var(--text2)",
          }}
        >
          {account.current_balance !== null ? formatCurrency(account.current_balance) : "—"}
        </div>
        {change !== null && (
          <div
            style={{
              fontSize: "10px",
              color: change.startsWith("+") ? "var(--up)" : "var(--liab)",
            }}
          >
            {change}
          </div>
        )}
      </div>
    </button>
  )
}

// ── Category group ────────────────────────────────────────────────────────────

function CategoryGroup({
  name,
  accounts,
  selectedId,
  onSelect,
  onAdd,
}: {
  name: CategoryName
  accounts: AccountResponse[]
  selectedId: string | null
  onSelect: (a: AccountResponse) => void
  onAdd: () => void
}) {
  const isPrimary = useAuth((s) => s.role === "primary")
  if (accounts.length === 0) return null
  const subtotal = groupSubtotal(accounts)
  const color = ACCOUNT_CATEGORY_COLORS[name] ?? "var(--muted)"

  return (
    <div style={{ marginBottom: "18px" }}>
      {/* Group header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "4px 14px 6px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              background: color,
              flexShrink: 0,
            }}
          />
          <span
            style={{
              fontSize: "10px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--faint)",
            }}
          >
            {name}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "11px", color: "var(--muted)" }}>
            {formatCurrency(String(subtotal))}
          </span>
          {isPrimary && (
            <button
              onClick={onAdd}
              aria-label={`Add ${name} account`}
              style={{
                width: "18px",
                height: "18px",
                borderRadius: "50%",
                background: "var(--bd2)",
                border: "none",
                cursor: "pointer",
                color: "var(--muted)",
                fontSize: "14px",
                lineHeight: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              +
            </button>
          )}
        </div>
      </div>
      {/* Account rows */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
        {accounts.map((a) => (
          <AccountRow
            key={a.id}
            account={a}
            category={name}
            selected={selectedId === a.id}
            onSelect={() => onSelect(a)}
          />
        ))}
      </div>
    </div>
  )
}

// ── Detail panel ──────────────────────────────────────────────────────────────

function DetailPanel({
  account,
  category,
  onArchive,
  onEdit,
}: {
  account: AccountResponse
  category: CategoryName
  onArchive: () => void
  onEdit: () => void
}) {
  const isPrimary = useAuth((s) => s.role === "primary")
  const isLiability = LIABILITY_TYPES.includes(account.account_type)
  const grad = isLiability ? "var(--pgrad)" : "var(--grad)"
  const accentBd = isLiability ? "var(--pbd)" : "var(--accent-bd)"
  const dot = ACCOUNT_CATEGORY_COLORS[category] ?? "var(--muted)"

  const { data: snapshots } = useQuery({
    queryKey: ["snapshots", account.id],
    queryFn: () => snapshotsApi.list(account.id),
    staleTime: 60_000,
  })

  const sparkData = useMemo(
    () =>
      (snapshots ?? [])
        .slice()
        .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
        .map((s) => ({ date: s.snapshot_date.slice(0, 7), balance: Number(s.balance) })),
    [snapshots],
  )

  const change = useMemo(() => {
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

  const lastUpdated = account.balance_as_of
    ? new Date(account.balance_as_of).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null

  return (
    <div
      style={{
        background: grad,
        border: `1px solid ${accentBd}`,
        borderRadius: "14px",
        overflow: "hidden",
        position: "sticky",
        top: "0",
      }}
    >
      {/* Header card */}
      <div style={{ padding: "20px 20px 16px" }}>
        <div
          style={{
            fontSize: "10px",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--label)",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            marginBottom: "8px",
          }}
        >
          <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: dot }} />
          {category}
          <span style={{ color: "var(--faint)" }}>·</span>
          <span>{ACCOUNT_LABELS[account.account_type]}</span>
        </div>
        <div
          style={{ fontSize: "18px", fontWeight: 700, color: "var(--text)", marginBottom: "2px" }}
        >
          {account.nickname}
        </div>
        {account.institution_name && (
          <div style={{ fontSize: "12px", color: "var(--muted)" }}>{account.institution_name}</div>
        )}
        {account.account_number_last4 && (
          <div style={{ fontSize: "12px", color: "var(--muted)" }}>
            {formatMaskedAccountNumber(account.account_number_last4)}
          </div>
        )}
        <div
          style={{
            fontSize: "32px",
            fontWeight: 700,
            color: isLiability ? "var(--liab)" : "var(--text)",
            marginTop: "14px",
            lineHeight: 1,
          }}
        >
          {account.current_balance !== null ? formatCurrency(account.current_balance) : "—"}
        </div>
        {change !== null && (
          <div
            style={{
              fontSize: "12px",
              color: change.startsWith("+") ? "var(--up)" : "var(--liab)",
              marginTop: "4px",
            }}
          >
            {change} vs previous snapshot
          </div>
        )}
        {lastUpdated && (
          <div style={{ fontSize: "11px", color: "var(--label)", marginTop: "6px" }}>
            Last updated {lastUpdated}
          </div>
        )}
      </div>

      {/* Sparkline */}
      {sparkData.length > 1 && (
        <div style={{ padding: "0 8px 8px" }}>
          <ResponsiveContainer width="100%" height={70}>
            <LineChart data={sparkData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" hide />
              <YAxis hide domain={["auto", "auto"]} />
              <Tooltip
                formatter={(v) => [formatCurrency(String(v ?? 0)), "Balance"]}
                contentStyle={{
                  background: "var(--card)",
                  border: "1px solid var(--bd2)",
                  borderRadius: "10px",
                  fontSize: 11,
                }}
                labelStyle={{ color: "var(--text3)", fontSize: 10 }}
              />
              <Line
                type="monotone"
                dataKey="balance"
                stroke={isLiability ? "#e0b48a" : "#46b888"}
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Notes section */}
      {account.notes && (
        <div
          style={{
            padding: "14px 20px",
            borderTop: `1px solid ${accentBd}`,
          }}
        >
          <div
            style={{
              fontSize: "10px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--label)",
              marginBottom: "6px",
            }}
          >
            Notes
          </div>
          <div style={{ fontSize: "12.5px", color: "var(--text3)", lineHeight: 1.5 }}>
            {account.notes}
          </div>
        </div>
      )}

      {/* Footer: transactions link + edit/archive */}
      <div
        style={{
          padding: "12px 20px",
          borderTop: `1px solid ${accentBd}`,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Link
          to="/accounts/$accountId/transactions"
          params={{ accountId: account.id }}
          style={{ fontSize: "12px", color: "var(--label)", textDecoration: "none" }}
        >
          View transactions →
        </Link>
        {isPrimary && (
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <button
              onClick={onEdit}
              style={{
                fontSize: "11px",
                color: "var(--label)",
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              Edit
            </button>
            <button
              onClick={onArchive}
              style={{
                fontSize: "11px",
                color: "var(--liab)",
                background: "none",
                border: "none",
                cursor: "pointer",
              }}
            >
              Archive
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Accounts() {
  const isPrimary = useAuth((s) => s.role === "primary")
  const {
    data: accounts,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
    staleTime: 60_000,
  })

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [archivingAccount, setArchivingAccount] = useState<AccountResponse | null>(null)
  const [editingAccount, setEditingAccount] = useState<AccountResponse | null>(null)

  // Prefetch snapshots for all visible accounts so AccountRow hits cache, not the network
  useQueries({
    queries: (accounts ?? []).map((account) => ({
      queryKey: ["snapshots", account.id],
      queryFn: () => snapshotsApi.list(account.id),
      staleTime: 60_000,
    })),
  })

  const groups = useMemo(() => categorise(accounts ?? []), [accounts])

  const selectedAccount = useMemo(
    () => accounts?.find((a) => a.id === selectedId) ?? null,
    [accounts, selectedId],
  )

  const selectedCategory = useMemo((): CategoryName | null => {
    if (!selectedAccount) return null
    for (const [name, list] of Object.entries(groups)) {
      if (list.some((a) => a.id === selectedAccount.id)) return name as CategoryName
    }
    return null
  }, [selectedAccount, groups])

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

  const categoryOrder: CategoryName[] = [
    "Banking & Cash",
    "Retirement",
    "Investments",
    "Real estate",
    "Liabilities",
  ]

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "20px",
        }}
      >
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Accounts
        </h1>
        {isPrimary && (
          <button
            onClick={() => setShowAdd(true)}
            style={{
              padding: "7px 16px",
              borderRadius: "9px",
              background: "var(--toggle-on-bg)",
              color: "var(--toggle-on-text)",
              border: "none",
              cursor: "pointer",
              fontSize: "13px",
              fontWeight: 500,
            }}
          >
            + Add account
          </button>
        )}
      </div>

      {/* Split panel */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: selectedAccount ? "1.5fr 1fr" : "1fr",
          gap: "16px",
          alignItems: "start",
        }}
        className="accounts-grid"
      >
        {/* Left: account list */}
        <div
          style={{
            background: "var(--card)",
            border: "1px solid var(--bd)",
            borderRadius: "14px",
            padding: "10px",
          }}
        >
          {accounts?.length === 0 ? (
            <div
              style={{
                padding: "48px 20px",
                textAlign: "center",
                color: "var(--muted)",
                fontSize: "13px",
              }}
            >
              No accounts yet. Add your first account to get started.
            </div>
          ) : (
            categoryOrder.map((name) => (
              <CategoryGroup
                key={name}
                name={name}
                accounts={groups[name]}
                selectedId={selectedId}
                onSelect={(a) => setSelectedId(a.id === selectedId ? null : a.id)}
                onAdd={() => setShowAdd(true)}
              />
            ))
          )}
        </div>

        {/* Right: detail panel (only when an account is selected) */}
        {selectedAccount && selectedCategory && (
          <DetailPanel
            account={selectedAccount}
            category={selectedCategory}
            onArchive={() => setArchivingAccount(selectedAccount)}
            onEdit={() => setEditingAccount(selectedAccount)}
          />
        )}
      </div>

      {showAdd && (
        <AddAccountModal allowedTypes={ACCOUNTS_PAGE_TYPES} onClose={() => setShowAdd(false)} />
      )}
      {archivingAccount && (
        <ArchiveAccountModal
          account={archivingAccount}
          onClose={() => {
            setArchivingAccount(null)
            setSelectedId(null)
          }}
        />
      )}
      {editingAccount && (
        <EditAccountModal account={editingAccount} onClose={() => setEditingAccount(null)} />
      )}
    </div>
  )
}
