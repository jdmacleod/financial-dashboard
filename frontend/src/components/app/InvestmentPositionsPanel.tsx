import { useQuery } from "@tanstack/react-query"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { investmentLotsApi } from "@/api/investmentLots"
import { formatCurrency } from "@/lib/formatters"

const ASSET_CLASS_LABELS: Record<string, string> = {
  equity: "Equity",
  fixed_income: "Fixed income",
  cash: "Cash",
  real_estate: "Real estate",
  alternative: "Alternatives",
  other: "Other",
  unclassified: "Unclassified",
}

// Stable palette so a given slice keeps its colour across renders.
const MIX_COLORS = ["#6c97c4", "#7bb89a", "#d9a566", "#b07cc6", "#cc7a7a", "#9aa0a6"]

function assetClassLabel(key: string): string {
  return ASSET_CLASS_LABELS[key] ?? key
}

export function InvestmentPositionsPanel() {
  const { data } = useQuery({
    queryKey: ["investment-positions"],
    queryFn: investmentLotsApi.positions,
    staleTime: 60_000,
  })

  // Nothing to show until at least one cost-basis lot exists.
  if (!data || data.positions.length === 0) return null

  const topPositions = data.positions.slice(0, 10)
  const mixData = data.holdings_mix.map((slice, i) => ({
    name: assetClassLabel(slice.asset_class),
    value: Number(slice.cost_basis),
    percentage: slice.percentage,
    color: MIX_COLORS[i % MIX_COLORS.length],
  }))

  return (
    <section
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
        Holdings
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.4fr 1fr",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* Top positions table */}
        <div>
          <div
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--text2)",
              marginBottom: "8px",
            }}
          >
            Top positions
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ color: "var(--faint)", fontSize: "11px", textAlign: "left" }}>
                <th style={{ padding: "4px 0", fontWeight: 500 }}>Ticker</th>
                <th style={{ padding: "4px 0", fontWeight: 500, textAlign: "right" }}>Shares</th>
                <th style={{ padding: "4px 0", fontWeight: 500, textAlign: "right" }}>
                  Cost basis
                </th>
              </tr>
            </thead>
            <tbody>
              {topPositions.map((p) => (
                <tr key={p.ticker} style={{ borderTop: "1px solid var(--bd)" }}>
                  <td style={{ padding: "7px 0", fontWeight: 600, color: "var(--text)" }}>
                    {p.ticker}
                  </td>
                  <td style={{ padding: "7px 0", textAlign: "right", color: "var(--label)" }}>
                    {Number(p.shares).toLocaleString()}
                  </td>
                  <td style={{ padding: "7px 0", textAlign: "right", color: "var(--label)" }}>
                    {formatCurrency(p.cost_basis)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: "8px", fontSize: "11px", color: "var(--faint)" }}>
            Cost basis shown — HearthLedger does not track live market prices.
          </div>
        </div>

        {/* Holdings mix donut */}
        <div>
          <div
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--text2)",
              marginBottom: "8px",
            }}
          >
            Holdings mix
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={mixData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={42}
                outerRadius={66}
                paddingAngle={2}
                stroke="none"
              >
                {mixData.map((slice) => (
                  <Cell key={slice.name} fill={slice.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v, _n, item) => [
                  `${formatCurrency(String(v ?? 0))} (${(item?.payload?.percentage ?? 0).toFixed(1)}%)`,
                  item?.payload?.name,
                ]}
                contentStyle={{
                  background: "var(--card)",
                  border: "1px solid var(--bd2)",
                  borderRadius: "10px",
                  fontSize: 11,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginTop: "8px" }}>
            {mixData.map((slice) => (
              <div
                key={slice.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "12px",
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "2px",
                      background: slice.color,
                      display: "inline-block",
                    }}
                  />
                  <span style={{ color: "var(--label)" }}>{slice.name}</span>
                </span>
                <span style={{ color: "var(--faint)" }}>{slice.percentage.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
