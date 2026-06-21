import { useState, useMemo } from "react"
import { Link, useRouterState } from "@tanstack/react-router"
import { useQuery, useQueries } from "@tanstack/react-query"
import { subDays, subYears, startOfYear, format } from "date-fns"
import { accountsApi } from "@/api/accounts"
import { propertiesApi } from "@/api/properties"
import { PROPERTY_TYPE_LABELS } from "@/lib/accountLabels"
import { formatCurrency } from "@/lib/formatters"
import { useAuth } from "@/hooks/useAuth"
import AddAccountModal from "@/components/app/AddAccountModal"
import ArchiveAccountModal from "@/components/app/ArchiveAccountModal"
import type { AccountResponse, AccountType } from "@/api/types"

const BRONZE = "#a9743f"
const ASSETS_PAGE_TYPES: AccountType[] = ["real_estate"]

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

// Compute delta from the range's start to the latest valuation
function valuationDelta(
  valuations: { valuation_date: string; estimated_value: string }[],
  from: string,
): { pct: number; isPositive: boolean } | null {
  if (valuations.length < 2) return null
  const sorted = [...valuations].sort((a, b) => b.valuation_date.localeCompare(a.valuation_date))
  const latest = Number(sorted[0].estimated_value)
  const baseline = sorted.find((v) => v.valuation_date <= from) ?? sorted[sorted.length - 1]
  const past = Number(baseline.estimated_value)
  if (past === 0) return null
  const pct = ((latest - past) / Math.abs(past)) * 100
  return { pct, isPositive: pct >= 0 }
}

// ── Property card ─────────────────────────────────────────────────────────────

function PropertyCard({ account, from }: { account: AccountResponse; from: string }) {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [archiving, setArchiving] = useState(false)

  const { data: property } = useQuery({
    queryKey: ["property-by-account", account.id],
    queryFn: () => propertiesApi.getByAccountId(account.id),
    staleTime: 60_000,
  })

  const { data: equity } = useQuery({
    queryKey: ["property-equity", property?.id],
    queryFn: () => propertiesApi.getEquity(property!.id),
    enabled: !!property?.id,
    staleTime: 60_000,
  })

  const { data: valuations } = useQuery({
    queryKey: ["property-valuations", property?.id],
    queryFn: () => propertiesApi.listValuations(property!.id),
    enabled: !!property?.id,
    staleTime: 60_000,
  })

  const delta = useMemo(() => valuationDelta(valuations ?? [], from), [valuations, from])

  const propertyValue = property?.current_estimated_value
    ? Number(property.current_estimated_value)
    : null
  const mortgageBalance = equity?.mortgage_balance ? Number(equity.mortgage_balance) : null
  const equityValue = equity?.equity ? Number(equity.equity) : null

  // Equity bar: proportion of property value that is equity
  const equityPct =
    propertyValue && propertyValue > 0 && equityValue !== null
      ? Math.max(0, Math.min(100, (equityValue / propertyValue) * 100))
      : null

  const propertyType = property?.property_type
    ? (PROPERTY_TYPE_LABELS[property.property_type] ?? property.property_type)
    : null

  return (
    <>
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
            style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}
          >
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "var(--text2)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {account.nickname}
              </div>
              {property && (
                <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px" }}>
                  {[propertyType, property.address].filter(Boolean).join(" · ")}
                </div>
              )}
              {property?.purchase_date && (
                <div style={{ fontSize: "10px", color: "var(--faint)", marginTop: "2px" }}>
                  Purchased {new Date(property.purchase_date).getFullYear()}
                  {property.purchase_price ? ` · ${formatCurrency(property.purchase_price)}` : ""}
                </div>
              )}
            </div>
            <div style={{ textAlign: "right", flexShrink: 0, marginLeft: "12px" }}>
              <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--text)" }}>
                {propertyValue !== null ? formatCurrency(String(propertyValue)) : "—"}
              </div>
              {delta !== null && (
                <div
                  style={{
                    fontSize: "11px",
                    color: delta.isPositive ? "var(--up)" : "var(--liab)",
                    marginTop: "2px",
                  }}
                >
                  {delta.isPositive ? "+" : ""}
                  {delta.pct.toFixed(1)}%
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Equity bar */}
        {equityPct !== null && (
          <div style={{ padding: "0 20px 14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "5px" }}>
              <span style={{ fontSize: "10px", color: "var(--muted)" }}>Equity</span>
              <span style={{ fontSize: "10px", color: "var(--muted)" }}>
                {equityValue !== null ? formatCurrency(String(equityValue)) : "—"}
                {mortgageBalance !== null && (
                  <span style={{ color: "var(--faint)" }}>
                    {" "}
                    / {formatCurrency(String(mortgageBalance))} mortgage
                  </span>
                )}
              </span>
            </div>
            {/* Bar track */}
            <div
              style={{
                height: "6px",
                borderRadius: "3px",
                background: "var(--track)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${equityPct}%`,
                  background: BRONZE,
                  borderRadius: "3px",
                  transition: "width 0.4s ease",
                }}
                aria-label={`${equityPct.toFixed(0)}% equity`}
              />
            </div>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "10px 20px",
            borderTop: "1px solid var(--bd)",
          }}
        >
          {property ? (
            <Link
              to="/properties/$propertyId"
              params={{ propertyId: property.id }}
              style={{ fontSize: "12px", color: "var(--muted)", textDecoration: "none" }}
            >
              View property →
            </Link>
          ) : (
            <span style={{ fontSize: "11px", color: "var(--faint)", fontStyle: "italic" }}>
              No property record
            </span>
          )}
          {isPrimary && (
            <button
              onClick={() => setArchiving(true)}
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
          )}
        </div>
      </div>

      {archiving && <ArchiveAccountModal account={account} onClose={() => setArchiving(false)} />}
    </>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Assets() {
  const isPrimary = useAuth((s) => s.role === "primary")
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
  const [showAdd, setShowAdd] = useState(false)

  // Stage 1: prefetch property records for all real-estate accounts
  const prefetchedPropertyQueries = useQueries({
    queries: (accounts ?? [])
      .filter((a) => a.account_type === "real_estate")
      .map((account) => ({
        queryKey: ["property-by-account", account.id],
        queryFn: () => propertiesApi.getByAccountId(account.id),
        staleTime: 60_000,
      })),
  })

  // Stage 2: prefetch equity + valuations for every resolved property
  const prefetchedPropertyIds = prefetchedPropertyQueries.flatMap((q) =>
    q.data?.id ? [q.data.id] : [],
  )
  useQueries({
    queries: prefetchedPropertyIds.flatMap((propertyId) => [
      {
        queryKey: ["property-equity", propertyId],
        queryFn: () => propertiesApi.getEquity(propertyId),
        staleTime: 60_000,
      },
      {
        queryKey: ["property-valuations", propertyId],
        queryFn: () => propertiesApi.listValuations(propertyId),
        staleTime: 60_000,
      },
    ]),
  })

  const realEstateAccounts = useMemo(
    () => (accounts ?? []).filter((a) => a.account_type === "real_estate"),
    [accounts],
  )

  const totalValue = useMemo(
    () => realEstateAccounts.reduce((s, a) => s + Number(a.current_balance ?? 0), 0),
    [realEstateAccounts],
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
    return <div style={{ padding: "32px", color: "var(--liab)" }}>Failed to load assets.</div>
  }

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
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
          Real estate
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
            + Add property
          </button>
        )}
      </div>

      {/* KPI summary */}
      {realEstateAccounts.length > 0 && (
        <div
          style={{
            background: "var(--grad)",
            border: "1px solid var(--accent-bd)",
            borderRadius: "14px",
            padding: "16px 20px",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "20px",
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
              Total property value
            </div>
            <div style={{ fontSize: "26px", fontWeight: 700, color: "var(--text)", lineHeight: 1 }}>
              {formatCurrency(String(totalValue))}
            </div>
          </div>
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: BRONZE }} />
          <div style={{ fontSize: "12px", color: "var(--label)" }}>
            {realEstateAccounts.length} propert{realEstateAccounts.length !== 1 ? "ies" : "y"}
          </div>
        </div>
      )}

      {/* Property cards */}
      {realEstateAccounts.length === 0 ? (
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
          No properties yet. Add a real estate account to get started.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {realEstateAccounts.map((a) => (
            <PropertyCard key={a.id} account={a} from={from} />
          ))}
        </div>
      )}

      {showAdd && (
        <AddAccountModal
          allowedTypes={ASSETS_PAGE_TYPES}
          label="asset"
          onClose={() => setShowAdd(false)}
        />
      )}
    </div>
  )
}
