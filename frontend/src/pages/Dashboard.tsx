import { useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  CartesianGrid,
} from "recharts"
import { useRouterState } from "@tanstack/react-router"
import { reportsApi } from "@/api/reports"
import { accountsApi } from "@/api/accounts"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { formatCurrency, formatMaskedAccountNumber } from "@/lib/formatters"
import { toIso } from "@/lib/dateRange"
import { startOfYear, subYears, subDays } from "date-fns"

type Range = "ytd" | "1y" | "all"

function useRange(): Range {
  const search = useRouterState({ select: (s) => s.location.search })
  return (new URLSearchParams(search).get("range") as Range) ?? "ytd"
}

function rangeToDateParams(
  range: Range,
  householdCreatedAt: string | null,
): { from: string; to: string } {
  const today = new Date()
  const to = toIso(today)
  if (range === "1y") return { from: toIso(subDays(today, 365)), to }
  if (range === "all") {
    const from = householdCreatedAt ? householdCreatedAt.slice(0, 10) : toIso(subYears(today, 10))
    return { from, to }
  }
  // ytd
  return { from: toIso(startOfYear(today)), to }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string
  sub?: string
  accent?: boolean
}) {
  return (
    <div
      style={{
        background: accent ? "var(--grad)" : "var(--card)",
        border: `1px solid ${accent ? "var(--accent-bd)" : "var(--bd)"}`,
        borderRadius: "14px",
        padding: "18px 20px",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: accent ? "var(--label)" : "var(--faint)",
          marginBottom: "6px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: accent ? "26px" : "22px",
          fontWeight: 700,
          color: accent ? "var(--text)" : "var(--text2)",
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "11px",
            color: accent ? "var(--label)" : "var(--muted)",
            marginTop: "5px",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  )
}

function SectionCard({
  children,
  style,
}: {
  children: React.ReactNode
  style?: React.CSSProperties
}) {
  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--bd)",
        borderRadius: "14px",
        padding: "18px 20px",
        ...style,
      }}
    >
      {children}
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: "13px",
        fontWeight: 600,
        color: "var(--text3)",
        marginBottom: "14px",
      }}
    >
      {children}
    </div>
  )
}

const DONUT_COLORS: Record<string, string> = {
  Banking: "#46d39a",
  Investments: "#6c97c4",
  Retirement: "#46b888",
  "Real estate": "#d9b96a",
  HSA: "#9fb3a8",
  Other: "#6f897c",
}

function compactCurrency(n: number): string {
  const sign = n < 0 ? "-" : ""
  const abs = Math.abs(n)
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}k`
  return `${sign}$${abs.toFixed(0)}`
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const range = useRange()
  const { householdName, isLoading: userLoading } = useCurrentUser()

  // We read household created_at separately for "all" range
  const { data: household } = useQuery({
    queryKey: ["household"],
    queryFn: async () => {
      const { householdApi } = await import("@/api/household")
      return householdApi.get()
    },
    staleTime: 5 * 60_000,
  })

  const dateParams = rangeToDateParams(range, household?.created_at ?? null)

  const { data: dash, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: reportsApi.dashboard,
    staleTime: 30_000,
  })

  const { data: nwReport } = useQuery({
    queryKey: ["reports", "net-worth", range, dateParams.from, dateParams.to],
    queryFn: () => reportsApi.netWorth(dateParams.from, dateParams.to, "monthly"),
    staleTime: 30_000,
  })

  const { data: cashFlowReport } = useQuery({
    queryKey: ["reports", "cash-flow", range, dateParams.from, dateParams.to],
    queryFn: () => reportsApi.cashFlow(dateParams.from, dateParams.to, "month"),
    staleTime: 30_000,
  })

  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
    staleTime: 60_000,
  })

  // Liquid = sum of checking + savings balances
  const liquid = useMemo(() => {
    if (!accounts) return null
    const sum = accounts
      .filter((a) => a.account_type === "checking" || a.account_type === "savings")
      .reduce((acc, a) => acc + Number(a.current_balance ?? 0), 0)
    return sum
  }, [accounts])

  // Net worth trend chart data
  const nwChartData = useMemo(
    () =>
      nwReport?.series.map((p) => ({
        date: p.date.slice(0, 7),
        value: Number(p.net_worth),
        assets: Number(p.total_assets),
      })) ?? [],
    [nwReport],
  )

  // Asset allocation donut from current breakdown
  const donutData = useMemo(() => {
    const b = nwReport?.current?.breakdown
    if (!b) return []
    const raw = [
      { name: "Banking", value: Number(b.checking_savings) },
      { name: "Investments", value: Number(b.investment) },
      { name: "Retirement", value: Number(b.retirement) },
      { name: "Real estate", value: Number(b.real_estate) },
      { name: "HSA", value: Number(b.hsa) },
      { name: "Other", value: Number(b.other_assets) },
    ]
    return raw.filter((d) => d.value > 0)
  }, [nwReport])

  // Cash flow bar chart (income vs expenses per period)
  const cfChartData = useMemo(
    () =>
      cashFlowReport?.series.map((p) => ({
        period: p.period.slice(0, 7),
        Income: Number(p.income),
        Expenses: Number(p.expenses),
      })) ?? [],
    [cashFlowReport],
  )

  // Top 5 accounts by balance (assets only)
  const topHoldings = useMemo(() => {
    if (!accounts) return []
    return [...accounts]
      .filter(
        (a) =>
          a.current_balance !== null &&
          ![
            "credit_card",
            "mortgage",
            "auto_loan",
            "personal_loan",
            "student_loan",
            "other_liability",
          ].includes(a.account_type),
      )
      .sort((a, b) => Number(b.current_balance) - Number(a.current_balance))
      .slice(0, 5)
  }, [accounts])

  const donutTotal = useMemo(() => donutData.reduce((s, d) => s + d.value, 0), [donutData])

  // Net worth trend range change (for sub-label)
  const nwRangeChange = useMemo(() => {
    if (nwChartData.length < 2) return null
    const start = nwChartData[0].value
    const end = nwChartData[nwChartData.length - 1].value
    const change = end - start
    const pct = start !== 0 ? (change / Math.abs(start)) * 100 : 0
    return { change, pct }
  }, [nwChartData])

  // Liabilities from nwReport breakdown
  const liabBreakdown = useMemo(() => {
    const b = nwReport?.current?.breakdown
    if (!b) return []
    return [
      { name: "Mortgage", value: Number(b.mortgage) },
      { name: "Other", value: Number(b.other_liabilities) },
    ].filter((d) => d.value > 0)
  }, [nwReport])

  const isLoading = dashLoading || userLoading
  if (isLoading && !dash) {
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

  const nwChange = Number(dash?.net_worth.change_30d ?? 0)
  const nwChangePct = dash?.net_worth.change_30d_pct

  return (
    <div
      style={{
        maxWidth: "1100px",
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      {/* Page heading */}
      <h1
        role="heading"
        aria-level={1}
        style={{ fontSize: "22px", fontWeight: 700, color: "var(--text)", margin: 0 }}
      >
        {householdName ?? "Dashboard"}
      </h1>

      {/* KPI row */}
      {dash && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: "12px",
          }}
        >
          <KpiCard
            label="Net Worth"
            value={formatCurrency(dash.net_worth.current)}
            sub={
              nwChangePct != null
                ? `${nwChange >= 0 ? "+" : ""}${nwChangePct.toFixed(1)}% vs 30d ago`
                : undefined
            }
            accent
          />
          <KpiCard label="Assets" value={formatCurrency(dash.accounts_summary.total_assets)} />
          <KpiCard
            label="Liabilities"
            value={formatCurrency(dash.accounts_summary.total_liabilities)}
            sub="total owed"
          />
          <KpiCard
            label="Liquid"
            value={liquid !== null ? formatCurrency(String(liquid)) : "—"}
            sub="checking + savings"
          />
          <KpiCard
            label="Saved / mo"
            value={formatCurrency(dash.cash_flow_mtd.net)}
            sub="month to date"
          />
        </div>
      )}

      {/* Net worth trend + asset donut */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: "12px" }}>
        <SectionCard>
          {/* Custom header with range sub-label matching design */}
          <div style={{ marginBottom: "14px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text3)" }}>
              Net worth trend
            </div>
            {nwRangeChange && (
              <div
                style={{
                  fontSize: "11px",
                  color: nwRangeChange.change >= 0 ? "var(--up)" : "var(--liab)",
                  marginTop: "2px",
                }}
              >
                {nwRangeChange.change >= 0 ? "+" : ""}
                {formatCurrency(String(Math.abs(nwRangeChange.change)))}
                {" · "}
                {nwRangeChange.change >= 0 ? "+" : ""}
                {nwRangeChange.pct.toFixed(1)}%{" "}
                {range === "1y" ? "trailing year" : range === "ytd" ? "YTD" : "all time"}
              </div>
            )}
          </div>
          {nwChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={nwChartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="nwGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#46b888" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#46b888" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: "var(--axis)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: string) => {
                    const [, m] = v.split("-")
                    return [
                      "Jan",
                      "Feb",
                      "Mar",
                      "Apr",
                      "May",
                      "Jun",
                      "Jul",
                      "Aug",
                      "Sep",
                      "Oct",
                      "Nov",
                      "Dec",
                    ][parseInt(m) - 1]
                  }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "var(--axis)" }}
                  tickLine={false}
                  axisLine={false}
                  width={52}
                  tickFormatter={(v: number) =>
                    v >= 1_000_000
                      ? `$${(v / 1_000_000).toFixed(1)}M`
                      : v >= 1000
                        ? `$${(v / 1000).toFixed(0)}k`
                        : `$${v}`
                  }
                />
                <Tooltip
                  formatter={(v) => [formatCurrency(String(v ?? 0)), "Net Worth"]}
                  labelStyle={{ color: "var(--text3)", fontSize: 11 }}
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--bd2)",
                    borderRadius: "10px",
                    fontSize: 12,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#46b888"
                  strokeWidth={2}
                  fill="url(#nwGrad)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div
              style={{
                height: "180px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--muted)",
                fontSize: "13px",
              }}
            >
              No data for this range
            </div>
          )}
        </SectionCard>

        <SectionCard>
          <SectionLabel>Asset allocation</SectionLabel>
          {donutData.length > 0 ? (
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              {/* Donut with center text overlay — extra 7px margin prevents arc clipping */}
              <div style={{ position: "relative", flexShrink: 0 }}>
                <PieChart width={152} height={152}>
                  <Pie
                    data={donutData}
                    cx={76}
                    cy={76}
                    innerRadius={54}
                    outerRadius={69}
                    paddingAngle={2}
                    dataKey="value"
                    strokeWidth={0}
                  >
                    {donutData.map((entry) => (
                      <Cell key={entry.name} fill={DONUT_COLORS[entry.name] ?? "#6f897c"} />
                    ))}
                  </Pie>
                </PieChart>
                {donutTotal > 0 && (
                  <div
                    style={{
                      position: "absolute",
                      top: "76px",
                      left: "76px",
                      transform: "translate(-50%, -50%)",
                      textAlign: "center",
                      pointerEvents: "none",
                    }}
                  >
                    <div
                      style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        color: "var(--text)",
                        lineHeight: 1.1,
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {compactCurrency(donutTotal)}
                    </div>
                    <div style={{ fontSize: "9px", color: "var(--muted)", marginTop: "2px" }}>
                      assets
                    </div>
                  </div>
                )}
              </div>
              {/* Legend with percentages */}
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
                {donutData.map((d) => {
                  const pct = donutTotal > 0 ? Math.round((d.value / donutTotal) * 100) : 0
                  return (
                    <div key={d.name} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span
                        style={{
                          width: "8px",
                          height: "8px",
                          borderRadius: "50%",
                          background: DONUT_COLORS[d.name] ?? "#6f897c",
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ flex: 1, fontSize: "11px", color: "var(--text3)" }}>
                        {d.name}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          color: "var(--muted)",
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {pct}%
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div
              style={{
                color: "var(--muted)",
                fontSize: "12px",
                textAlign: "center",
                marginTop: "30px",
              }}
            >
              No data
            </div>
          )}
        </SectionCard>
      </div>

      {/* Bottom row: cash flow | holdings | liabilities */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
        {/* Cash flow bars */}
        <SectionCard>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "14px",
            }}
          >
            <SectionLabel>Cash flow</SectionLabel>
            <Link
              to="/reports/cash-flow"
              style={{ fontSize: "11px", color: "var(--label)", textDecoration: "none" }}
            >
              Full report →
            </Link>
          </div>
          {cfChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={140}>
              <BarChart
                data={cfChartData}
                barSize={10}
                margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
              >
                <CartesianGrid vertical={false} stroke="var(--grid)" />
                <XAxis
                  dataKey="period"
                  tick={{ fontSize: 9, fill: "var(--axis)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: "var(--axis)" }}
                  tickLine={false}
                  axisLine={false}
                  width={38}
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip
                  formatter={(v, name) => [formatCurrency(String(v ?? 0)), String(name)]}
                  contentStyle={{
                    background: "var(--card)",
                    border: "1px solid var(--bd2)",
                    borderRadius: "10px",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="Income" fill="var(--up)" radius={[3, 3, 0, 0]} />
                <Bar dataKey="Expenses" fill="var(--liab)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div
              style={{
                height: "140px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--muted)",
                fontSize: "12px",
              }}
            >
              No data for this range
            </div>
          )}
        </SectionCard>

        {/* Liabilities breakdown */}
        <SectionCard>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "14px",
            }}
          >
            <SectionLabel>Liabilities</SectionLabel>
            <Link
              to="/debt"
              style={{ fontSize: "11px", color: "var(--label)", textDecoration: "none" }}
            >
              Manage →
            </Link>
          </div>
          {liabBreakdown.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {liabBreakdown.map((l) => (
                <div
                  key={l.name}
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
                >
                  <span style={{ fontSize: "12.5px", color: "var(--text3)" }}>{l.name}</span>
                  <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--liab)" }}>
                    {formatCurrency(String(l.value))}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: "12px" }}>No liabilities</div>
          )}
        </SectionCard>

        {/* Largest holdings */}
        <SectionCard>
          <SectionLabel>Largest holdings</SectionLabel>
          {topHoldings.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {topHoldings.map((a) => (
                <div
                  key={a.id}
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
                >
                  <div>
                    <div style={{ fontSize: "12.5px", color: "var(--text3)", fontWeight: 500 }}>
                      {a.nickname}
                    </div>
                    {(a.institution_name || a.account_number_last4) && (
                      <div style={{ fontSize: "10px", color: "var(--muted)" }}>
                        {[a.institution_name, formatMaskedAccountNumber(a.account_number_last4)]
                          .filter(Boolean)
                          .join(" · ")}
                      </div>
                    )}
                  </div>
                  <div style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--text)" }}>
                    {a.current_balance !== null ? formatCurrency(a.current_balance) : "—"}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: "var(--muted)", fontSize: "12px" }}>No accounts yet</div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}
