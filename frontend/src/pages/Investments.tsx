import { useMemo } from "react"
import { useQuery, useQueries } from "@tanstack/react-query"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts"
import { accountsApi } from "@/api/accounts"
import { snapshotsApi } from "@/api/snapshots"
import { BROKERAGE_ACCOUNT_TYPES } from "@/lib/accountTypes"
import { formatCurrency, formatMaskedAccountNumber } from "@/lib/formatters"
import type { AccountResponse } from "@/api/types"

const ACCENT = "#6c97c4"

// ── Account card with snapshot history ───────────────────────────────────────

function InvestmentCard({ account }: { account: AccountResponse }) {
  const { data: snapshots } = useQuery({
    queryKey: ["snapshots", account.id],
    queryFn: () => snapshotsApi.list(account.id),
    staleTime: 60_000,
  })

  const chartData = useMemo(
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
    return { pct, isPositive: pct >= 0 }
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
                {change.pct.toFixed(1)}% vs prev
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

export default function Investments() {
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
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {investmentAccounts.map((a) => (
            <InvestmentCard key={a.id} account={a} />
          ))}
        </div>
      )}
    </div>
  )
}
