import { useState, useMemo, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useRouterState, useNavigate, Link } from "@tanstack/react-router"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts"
import { subDays, subYears, startOfYear } from "date-fns"
import { reportsApi } from "@/api/reports"
import { categoriesApi } from "@/api/categories"
import { formatCurrency } from "@/lib/formatters"
import { toIso } from "@/lib/dateRange"

type GroupBy = "month" | "quarter"
type Range = "ytd" | "1y" | "all"

function useRange(): Range {
  const search = useRouterState({ select: (s) => s.location.search })
  return (new URLSearchParams(search).get("range") as Range) ?? "ytd"
}

function rangeToDateParams(range: Range): { from: string; to: string } {
  const today = new Date()
  const to = toIso(today)
  if (range === "1y") return { from: toIso(subDays(today, 365)), to }
  if (range === "all") return { from: toIso(subYears(today, 10)), to }
  return { from: toIso(startOfYear(today)), to }
}

function useIsMobile() {
  const [mobile, setMobile] = useState(
    typeof window !== "undefined" ? window.innerWidth < 768 : false,
  )
  useEffect(() => {
    const handler = () => setMobile(window.innerWidth < 768)
    window.addEventListener("resize", handler)
    return () => window.removeEventListener("resize", handler)
  }, [])
  return mobile
}

// ── KPI card ─────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  accent,
  negative,
}: {
  label: string
  value: string
  accent?: boolean
  negative?: boolean
}) {
  const color = accent ? "var(--text)" : negative ? "var(--liab)" : "var(--up)"

  return (
    <div
      style={{
        background: accent ? "var(--grad)" : "var(--card)",
        border: `1px solid ${accent ? "var(--accent-bd)" : "var(--bd)"}`,
        borderRadius: "14px",
        padding: "16px 18px",
      }}
    >
      <div
        style={{
          fontSize: "10px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: accent ? "var(--label)" : "var(--faint)",
          marginBottom: "6px",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: "20px", fontWeight: 700, color, lineHeight: 1 }}>{value}</div>
    </div>
  )
}

// Category bar (horizontal) — renders as button when onClick is provided
function CategoryBar({
  name,
  amount,
  percentage,
  max,
  color,
  onClick,
}: {
  name: string
  amount: string
  percentage: number
  max: number
  color?: string
  onClick?: () => void
}) {
  const barWidth = max > 0 ? (Math.abs(Number(amount)) / max) * 100 : 0

  const inner = (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "3px" }}>
        <span style={{ fontSize: "12px", color: "var(--text3)" }}>{name}</span>
        <span style={{ fontSize: "12px", color: "var(--muted)" }}>
          {formatCurrency(String(Math.abs(Number(amount))))}
          <span style={{ fontSize: "10px", color: "var(--faint)", marginLeft: "4px" }}>
            {percentage.toFixed(0)}%
          </span>
        </span>
      </div>
      <div
        style={{
          height: "4px",
          borderRadius: "2px",
          background: "var(--track)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${barWidth}%`,
            background: color ?? "var(--liab)",
            borderRadius: "2px",
          }}
        />
      </div>
    </>
  )

  if (onClick) {
    return (
      <button
        onClick={onClick}
        aria-label={`View ${name} spending detail`}
        style={{
          display: "block",
          width: "100%",
          marginBottom: "10px",
          padding: "6px 8px",
          background: "transparent",
          border: "none",
          borderRadius: "6px",
          cursor: "pointer",
          textAlign: "left",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "rgba(255,255,255,0.04)"
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent"
        }}
        onFocus={(e) => {
          e.currentTarget.style.outline = "2px solid var(--accent)"
        }}
        onBlur={(e) => {
          e.currentTarget.style.outline = "none"
        }}
      >
        {inner}
      </button>
    )
  }

  return <div style={{ marginBottom: "10px" }}>{inner}</div>
}

function formatPeriodLabel(period: string): string {
  if (period.includes("-Q")) {
    const [year, q] = period.split("-")
    return `${q} ${year}`
  }
  const [year, month] = period.split("-")
  const d = new Date(Number(year), Number(month) - 1, 1)
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" })
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ReportCashFlow() {
  const [groupBy, setGroupBy] = useState<GroupBy>("month")

  const range = useRange()
  const dateRange = rangeToDateParams(range)
  const navigate = useNavigate()
  const isMobile = useIsMobile()

  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "cash-flow", dateRange.from, dateRange.to, groupBy],
    queryFn: () => reportsApi.cashFlow(dateRange.from, dateRange.to, groupBy),
  })

  const { data: spending } = useQuery({
    queryKey: ["reports", "spending-by-category", dateRange.from, dateRange.to],
    queryFn: () => reportsApi.spendingByCategory(dateRange.from, dateRange.to),
    staleTime: 30_000,
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
    staleTime: 5 * 60 * 1000,
  })

  const chartData = useMemo(
    () =>
      data?.series.map((p) => ({
        period: p.period.slice(0, 7),
        Income: Number(p.income),
        Expenses: Math.abs(Number(p.expenses)),
        isPositive: Number(p.net) >= 0,
      })) ?? [],
    [data],
  )

  const maxSpend = useMemo(
    () =>
      spending ? Math.max(0, ...spending.categories.map((c) => Math.abs(Number(c.amount)))) : 0,
    [spending],
  )

  const categoryColorMap = useMemo(() => {
    const map = new Map<string, string>()
    for (const c of categories ?? []) {
      map.set(c.id, c.color_hex)
    }
    return map
  }, [categories])

  const savingsRateStr = data?.totals ? `${data.totals.savings_rate.toFixed(1)}%` : "—"
  const netPositive = data?.totals ? Number(data.totals.net) >= 0 : true

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Cash Flow
        </h1>
      </div>

      {/* Group-by control — date range is driven by the global YTD / 1Y / All toggle */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "16px" }}>
        {(["month", "quarter"] as GroupBy[]).map((g) => (
          <button
            key={g}
            onClick={() => setGroupBy(g)}
            style={{
              padding: "4px 12px",
              borderRadius: "20px",
              fontSize: "12px",
              fontWeight: 500,
              border: `1px solid ${groupBy === g ? "transparent" : "var(--bd)"}`,
              background: groupBy === g ? "var(--toggle-on-bg)" : "transparent",
              color: groupBy === g ? "var(--toggle-on-text)" : "var(--muted)",
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {g}
          </button>
        ))}
      </div>

      {isLoading && (
        <div style={{ padding: "48px 0", textAlign: "center", color: "var(--muted)" }}>
          Loading…
        </div>
      )}
      {error && (
        <div style={{ padding: "24px 0", color: "var(--liab)" }}>Failed to load report.</div>
      )}

      {data?.totals && (
        <>
          {/* 4 KPI cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(4, 1fr)",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            <KpiCard label="Total income" value={formatCurrency(data.totals.income)} />
            <KpiCard
              label="Total expenses"
              value={formatCurrency(String(Math.abs(Number(data.totals.expenses))))}
              negative
            />
            <KpiCard
              label="Net saved"
              value={formatCurrency(data.totals.net)}
              accent={netPositive}
              negative={!netPositive}
            />
            <KpiCard label="Savings rate" value={savingsRateStr} />
          </div>

          {/* 12-month bar chart */}
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--bd)",
              borderRadius: "14px",
              padding: "18px 20px",
              marginBottom: "16px",
            }}
          >
            <div
              style={{
                fontSize: "11px",
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--faint)",
                marginBottom: "14px",
              }}
            >
              Income vs Expenses
            </div>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barCategoryGap="30%" barGap={2}>
                  <CartesianGrid stroke="var(--axis)" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="period"
                    tick={{ fontSize: 10, fill: "var(--muted)" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={formatPeriodLabel}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: "var(--muted)" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) =>
                      v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                    }
                    width={44}
                  />
                  <Tooltip
                    formatter={(v) => [formatCurrency(String(v ?? 0)), ""]}
                    contentStyle={{
                      background: "var(--card)",
                      border: "1px solid var(--bd2)",
                      borderRadius: "10px",
                      fontSize: 11,
                    }}
                    labelStyle={{ color: "var(--text3)", fontSize: 10 }}
                  />
                  <Bar dataKey="Income" radius={[3, 3, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill="var(--up)" />
                    ))}
                  </Bar>
                  <Bar dataKey="Expenses" radius={[3, 3, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill="var(--liab)" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div
                style={{
                  padding: "32px 0",
                  textAlign: "center",
                  color: "var(--faint)",
                  fontSize: "12px",
                }}
              >
                No data for this period.
              </div>
            )}
          </div>

          {/* Retirement income breakdown — hidden unless the household draws
              Social Security, a pension, or RMDs. */}
          {data.retirement_income?.has_data && (
            <div
              style={{
                background: "var(--card)",
                border: "1px solid var(--bd)",
                borderRadius: "14px",
                padding: "18px 20px",
                marginBottom: "16px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "var(--faint)",
                  marginBottom: "14px",
                }}
              >
                Retirement income
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(4, 1fr)",
                  gap: "12px",
                }}
              >
                {[
                  { label: "Social Security", value: data.retirement_income.social_security },
                  { label: "Pension", value: data.retirement_income.pension },
                  { label: "RMDs", value: data.retirement_income.rmd },
                  { label: "Total", value: data.retirement_income.total, accent: true },
                ].map((bucket) => (
                  <div key={bucket.label}>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "var(--faint)",
                        marginBottom: "4px",
                      }}
                    >
                      {bucket.label}
                    </div>
                    <div
                      style={{
                        fontSize: "18px",
                        fontWeight: 700,
                        color: bucket.accent ? "var(--up)" : "var(--text)",
                      }}
                    >
                      {formatCurrency(bucket.value)}
                    </div>
                  </div>
                ))}
              </div>
              {data.retirement_income.federal_tax_estimate && (
                <div
                  style={{
                    marginTop: "14px",
                    paddingTop: "12px",
                    borderTop: "1px solid var(--bd)",
                    display: "flex",
                    flexWrap: "wrap",
                    justifyContent: "space-between",
                    gap: "8px",
                    fontSize: "12px",
                    color: "var(--text2)",
                  }}
                >
                  <span>
                    Est. federal tax ({data.retirement_income.federal_tax_estimate.tax_year}):{" "}
                    <strong style={{ color: "var(--liab)" }}>
                      {formatCurrency(data.retirement_income.federal_tax_estimate.federal_tax)}
                    </strong>{" "}
                    · after-tax{" "}
                    <strong style={{ color: "var(--up)" }}>
                      {formatCurrency(data.retirement_income.federal_tax_estimate.after_tax_income)}
                    </strong>{" "}
                    ({(data.retirement_income.federal_tax_estimate.marginal_rate * 100).toFixed(0)}%
                    marginal)
                  </span>
                  <span style={{ color: "var(--faint)" }}>
                    Estimate — federal only, retirement income basis
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Bottom row: category breakdown + period table */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isMobile ? "1fr" : "1fr 1.5fr",
              gap: "14px",
            }}
          >
            {/* Spending by category */}
            {spending && spending.categories.length > 0 && (
              <div
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--bd)",
                  borderRadius: "14px",
                  padding: "18px 20px",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "var(--faint)",
                    marginBottom: "14px",
                  }}
                >
                  Top spending categories
                </div>
                {spending.categories.slice(0, 8).map((c) => (
                  <CategoryBar
                    key={c.category_id ?? c.name}
                    name={c.name}
                    amount={c.amount}
                    percentage={c.percentage}
                    max={maxSpend}
                    color={
                      c.category_id ? (categoryColorMap.get(c.category_id) ?? "#888888") : undefined
                    }
                    onClick={
                      c.category_id
                        ? () =>
                            void navigate({
                              to: "/reports/spending",
                              search: { category: c.category_id! },
                            })
                        : undefined
                    }
                  />
                ))}
                <div style={{ textAlign: "right", marginTop: "8px" }}>
                  <Link
                    to="/reports/spending"
                    search={{ category: undefined }}
                    style={{ fontSize: "11px", color: "var(--faint)", textDecoration: "none" }}
                  >
                    View full breakdown →
                  </Link>
                </div>
              </div>
            )}

            {/* Period table */}
            {data.series.length > 0 && (
              <div
                style={{
                  background: "var(--card)",
                  border: "1px solid var(--bd)",
                  borderRadius: "14px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                    color: "var(--faint)",
                    padding: "14px 16px 0",
                    marginBottom: "8px",
                  }}
                >
                  By period
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--bd)" }}>
                      {["Period", "Income", "Expenses", "Net", "Rate"].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "6px 12px",
                            textAlign: h === "Period" ? "left" : "right",
                            fontSize: "10px",
                            fontWeight: 600,
                            color: "var(--faint)",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...data.series].reverse().map((p) => {
                      const isPositive = Number(p.net) >= 0
                      return (
                        <tr key={p.period} style={{ borderBottom: "1px solid var(--bd)" }}>
                          <td
                            style={{ padding: "7px 12px", fontSize: "12px", color: "var(--muted)" }}
                          >
                            {formatPeriodLabel(p.period.slice(0, 7))}
                          </td>
                          <td
                            style={{
                              padding: "7px 12px",
                              fontSize: "12px",
                              color: "var(--up)",
                              textAlign: "right",
                            }}
                          >
                            {formatCurrency(p.income)}
                          </td>
                          <td
                            style={{
                              padding: "7px 12px",
                              fontSize: "12px",
                              color: "var(--liab)",
                              textAlign: "right",
                            }}
                          >
                            {formatCurrency(String(Math.abs(Number(p.expenses))))}
                          </td>
                          <td
                            style={{
                              padding: "7px 12px",
                              fontSize: "12px",
                              fontWeight: 600,
                              color: isPositive ? "var(--up)" : "var(--liab)",
                              textAlign: "right",
                            }}
                          >
                            {formatCurrency(p.net)}
                          </td>
                          <td
                            style={{
                              padding: "7px 12px",
                              fontSize: "12px",
                              color: "var(--muted)",
                              textAlign: "right",
                            }}
                          >
                            {p.savings_rate.toFixed(1)}%
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
