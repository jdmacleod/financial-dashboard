import { useMemo, useState } from "react"
import { useQuery, useQueries } from "@tanstack/react-query"
import { useRouterState } from "@tanstack/react-router"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { subDays, subYears, startOfYear, format } from "date-fns"
import { accountsApi } from "@/api/accounts"
import { snapshotsApi } from "@/api/snapshots"
import { EquityGrantsPanel } from "@/components/app/EquityGrantsPanel"
import { InvestmentPositionsPanel } from "@/components/app/InvestmentPositionsPanel"
import { InvestmentLotsPanel } from "@/components/app/InvestmentLotsPanel"
import { CapitalCommitmentsPanel } from "@/components/app/CapitalCommitmentsPanel"
import { BROKERAGE_ACCOUNT_TYPES } from "@/lib/accountTypes"
import { formatCurrency, formatMaskedAccountNumber } from "@/lib/formatters"
import { loadSort, persistSort } from "@/lib/sortStorage"
import type { AccountResponse } from "@/api/types"

type Range = "ytd" | "1y" | "all"

function useRange(): Range {
  const search = useRouterState({ select: (s) => s.location.search })
  return (new URLSearchParams(search).get("range") as Range) ?? "ytd"
}

function rangeFrom(range: Range): string {
  const today = new Date()
  if (range === "1y") return format(subDays(today, 365), "yyyy-MM-dd")
  if (range === "all") return format(subYears(today, 10), "yyyy-MM-dd")
  return format(startOfYear(today), "yyyy-MM-dd")
}

const ACCENT = "#6c97c4"

// ── Account card with snapshot history ───────────────────────────────────────

function InvestmentCard({ account, from }: { account: AccountResponse; from: string }) {
  const { data: snapshots } = useQuery({
    queryKey: ["snapshots", account.id],
    queryFn: () => snapshotsApi.list(account.id),
    staleTime: 60_000,
  })

  const chartData = useMemo(
    () =>
      (snapshots ?? [])
        .filter((s) => s.snapshot_date >= from)
        .slice()
        .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
        .map((s) => ({ date: s.snapshot_date.slice(0, 7), balance: Number(s.balance) })),
    [snapshots, from],
  )

  const change = useMemo(() => {
    if (!snapshots || snapshots.length < 2) return null
    const sorted = [...snapshots].sort(
      (a, b) => new Date(b.snapshot_date).getTime() - new Date(a.snapshot_date).getTime(),
    )
    const latest = Number(sorted[0].balance)
    const baseline = sorted.find((s) => s.snapshot_date <= from) ?? sorted[sorted.length - 1]
    const baselineBalance = Number(baseline.balance)
    if (baselineBalance === 0) return null
    const pct = ((latest - baselineBalance) / Math.abs(baselineBalance)) * 100
    return { pct, isPositive: pct >= 0 }
  }, [snapshots, from])

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
        background: "var(--card)",
        border: "1px solid var(--bd)",
        borderRadius: "14px",
        overflow: "hidden",
      }}
    >
      {/* Card header */}
      <div style={{ padding: "18px 20px 14px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "12px",
          }}
        >
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: "13px",
                fontWeight: 600,
                color: "var(--text2)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {account.nickname}
            </div>
            {(account.institution_name || account.account_number_last4) && (
              <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px" }}>
                {[account.institution_name, formatMaskedAccountNumber(account.account_number_last4)]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
            )}
          </div>
          <div style={{ textAlign: "right", flexShrink: 0 }}>
            <div style={{ fontSize: "17px", fontWeight: 700, color: "var(--text)" }}>
              {account.current_balance !== null ? formatCurrency(account.current_balance) : "—"}
            </div>
            {change !== null && (
              <div
                style={{
                  fontSize: "11px",
                  color: change.isPositive ? "var(--up)" : "var(--liab)",
                  marginTop: "2px",
                }}
              >
                {change.isPositive ? "+" : ""}
                {change.pct.toFixed(1)}%
              </div>
            )}
            {lastUpdated && (
              <div style={{ fontSize: "10px", color: "var(--faint)", marginTop: "2px" }}>
                {lastUpdated}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Snapshot history chart */}
      {chartData.length > 1 ? (
        <div style={{ padding: "0 8px 12px" }}>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--axis)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "var(--muted)" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--muted)" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) =>
                  v >= 1_000_000
                    ? `$${(v / 1_000_000).toFixed(1)}M`
                    : v >= 1000
                      ? `$${(v / 1000).toFixed(0)}k`
                      : `$${v}`
                }
                width={48}
              />
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
                stroke={ACCENT}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 3, fill: ACCENT }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div
          style={{
            padding: "12px 20px 16px",
            fontSize: "11px",
            color: "var(--faint)",
            fontStyle: "italic",
          }}
        >
          No snapshot history yet — add snapshots to see the balance chart.
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

type InvestmentSort = "value_desc" | "name_asc"
const INVESTMENT_SORTS: readonly InvestmentSort[] = ["value_desc", "name_asc"]
const INVESTMENT_SORT_KEY = "hl.investments.sort"

export default function Investments() {
  const range = useRange()
  const from = rangeFrom(range)

  const {
    data: accounts,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
    staleTime: 60_000,
  })

  // Prefetch snapshots for all investment accounts so InvestmentCard hits cache, not the network
  useQueries({
    queries: (accounts ?? [])
      .filter((a) => BROKERAGE_ACCOUNT_TYPES.includes(a.account_type))
      .map((account) => ({
        queryKey: ["snapshots", account.id],
        queryFn: () => snapshotsApi.list(account.id),
        staleTime: 60_000,
      })),
  })

  const investmentAccounts = useMemo(
    () => (accounts ?? []).filter((a) => BROKERAGE_ACCOUNT_TYPES.includes(a.account_type)),
    [accounts],
  )

  const totalBalance = useMemo(
    () => investmentAccounts.reduce((s, a) => s + Number(a.current_balance ?? 0), 0),
    [investmentAccounts],
  )

  const [sort, setSort] = useState<InvestmentSort>(() =>
    loadSort(INVESTMENT_SORT_KEY, INVESTMENT_SORTS, "value_desc"),
  )
  const changeSort = (next: InvestmentSort) => {
    setSort(next)
    persistSort(INVESTMENT_SORT_KEY, next)
  }
  const sortedAccounts = useMemo(() => {
    return [...investmentAccounts].sort((a, b) => {
      if (sort === "value_desc")
        return Number(b.current_balance ?? 0) - Number(a.current_balance ?? 0)
      if (sort === "name_asc") return a.nickname.localeCompare(b.nickname)
      return 0
    })
  }, [investmentAccounts, sort])

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
          Investments
        </h1>
      </div>

      {/* KPI summary card */}
      {investmentAccounts.length > 0 && (
        <div
          style={{
            background: "var(--grad)",
            border: "1px solid var(--accent-bd)",
            borderRadius: "14px",
            padding: "18px 20px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "20px",
          }}
        >
          <div>
            <div
              style={{
                fontSize: "11px",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--label)",
                marginBottom: "4px",
              }}
            >
              Total brokerage
            </div>
            <div style={{ fontSize: "28px", fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>
              {formatCurrency(String(totalBalance))}
            </div>
          </div>
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: ACCENT,
              flexShrink: 0,
            }}
          />
          <div style={{ fontSize: "12px", color: "var(--label)" }}>
            {investmentAccounts.length} brokerage account
            {investmentAccounts.length !== 1 ? "s" : ""}
          </div>
        </div>
      )}

      {/* Account cards */}
      {investmentAccounts.length === 0 ? (
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
          No brokerage accounts yet. Add an investment brokerage account to get started.
        </div>
      ) : (
        <>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              marginBottom: "12px",
            }}
          >
            <label
              htmlFor="investment-sort"
              style={{ fontSize: "12px", color: "var(--label)", marginRight: "8px" }}
            >
              Sort by
            </label>
            <select
              id="investment-sort"
              aria-label="Sort accounts"
              value={sort}
              onChange={(e) => changeSort(e.target.value as InvestmentSort)}
              style={{
                fontSize: "12px",
                color: "var(--text2)",
                background: "var(--card)",
                border: "1px solid var(--bd)",
                borderRadius: "8px",
                padding: "5px 8px",
                cursor: "pointer",
              }}
            >
              <option value="value_desc">Value ↓</option>
              <option value="name_asc">Name A–Z</option>
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {sortedAccounts.map((a) => (
              <InvestmentCard key={a.id} account={a} from={from} />
            ))}
          </div>
        </>
      )}

      {/* Demo-data extension surfaces — each renders nothing when empty. */}
      <div style={{ display: "flex", flexDirection: "column", gap: "20px", marginTop: "20px" }}>
        <InvestmentPositionsPanel />
        <EquityGrantsPanel />
        <InvestmentLotsPanel />
        <CapitalCommitmentsPanel />
      </div>
    </div>
  )
}
