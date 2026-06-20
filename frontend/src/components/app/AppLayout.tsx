import { useEffect, useRef, useState } from "react"
import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/hooks/useAuth"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { useTheme } from "@/stores/themeStore"
import { ExportModal } from "@/components/app/ExportModal"
import { accountsApi } from "@/api/accounts"
import { reportsApi } from "@/api/reports"
import { formatCurrency } from "@/lib/formatters"

type Range = "ytd" | "1y" | "all"

function useRange(): [Range, (r: Range) => void] {
  const search = useRouterState({ select: (s) => s.location.search })
  const params = new URLSearchParams(search)
  const range = (params.get("range") as Range) ?? "ytd"
  const setRange = (r: Range) => {
    const url = new URL(window.location.href)
    url.searchParams.set("range", r)
    window.history.replaceState(null, "", url.pathname + url.search)
    // Notify TanStack Router that the URL changed so location state updates
    window.dispatchEvent(new PopStateEvent("popstate"))
  }
  return [range, setRange]
}

function SidebarNavLink({
  to,
  children,
  onClick,
}: {
  to: string
  children: React.ReactNode
  onClick?: () => void
}) {
  const location = useRouterState({ select: (s) => s.location })
  const isActive = location.pathname === to || (to !== "/" && location.pathname.startsWith(to))
  return (
    <Link
      to={to}
      onClick={onClick}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors"
      style={{
        color: isActive ? "var(--nav-active-text)" : "var(--nav-text)",
        background: isActive ? "var(--nav-active-bg)" : "transparent",
      }}
    >
      {children}
    </Link>
  )
}

export function AppLayout() {
  const isPrimary = useAuth((s) => s.role === "primary")
  const logout = useAuth((s) => s.logout)
  const navigate = useNavigate()
  const { displayName, firstName, initials, householdName, role } = useCurrentUser()
  const { theme, setTheme } = useTheme()

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  const [range, setRange] = useRange()

  const accountsQuery = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
    staleTime: 60_000,
  })
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: reportsApi.dashboard,
    staleTime: 30_000,
  })

  const accountCount = accountsQuery.data?.length ?? null
  const netWorth = dashboardQuery.data?.net_worth.current ?? null

  const roleLabel =
    role === "primary" ? "Full access" : role === "partner" ? "Partner" : "View only"
  const roleRingColor = role === "primary" ? "#46b888" : role === "partner" ? "#6c97c4" : "#9fb3a8"

  async function handleLogout() {
    setUserMenuOpen(false)
    await logout()
    navigate({ to: "/login" })
  }

  // Close user menu on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setUserMenuOpen(false)
        setSidebarOpen(false)
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [])

  // Close user menu on outside click
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    if (userMenuOpen) document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [userMenuOpen])

  const today = new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })

  const sidebar = (
    <aside
      style={{
        width: "214px",
        flexShrink: 0,
        background: "var(--sidebar)",
        borderRight: "1px solid var(--bd)",
        display: "flex",
        flexDirection: "column",
        padding: "22px 16px",
        height: "100vh",
        position: "sticky",
        top: 0,
        overflowY: "auto",
      }}
    >
      {/* Brand mark */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "11px",
          padding: "0 6px 22px",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: "var(--toggle-on-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="2" width="5" height="5" rx="1.5" fill="rgba(255,255,255,0.85)" />
            <rect x="9" y="2" width="5" height="5" rx="1.5" fill="rgba(255,255,255,0.85)" />
            <rect x="2" y="9" width="5" height="5" rx="1.5" fill="rgba(255,255,255,0.85)" />
            <rect x="9" y="9" width="5" height="5" rx="1.5" fill="rgba(255,255,255,0.85)" />
          </svg>
        </div>
        <div>
          <div
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: "var(--text)",
              fontFamily: "'Spectral', serif",
            }}
          >
            {householdName ?? "HearthLedger"}
          </div>
          <div
            style={{
              fontSize: "10px",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "var(--faint)",
            }}
          >
            Wealth ledger
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "2px" }}>
        <SidebarNavLink to="/" onClick={() => setSidebarOpen(false)}>
          <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor">
            <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.5" />
            <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.5" />
            <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.5" />
            <rect x="9" y="9" width="5.5" height="5.5" rx="1.5" />
          </svg>
          Overview
        </SidebarNavLink>
        <SidebarNavLink to="/accounts" onClick={() => setSidebarOpen(false)}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          >
            <line x1="2" y1="4.5" x2="14" y2="4.5" />
            <line x1="2" y1="8.5" x2="14" y2="8.5" />
            <line x1="2" y1="12.5" x2="14" y2="12.5" />
          </svg>
          Accounts
        </SidebarNavLink>
        <SidebarNavLink to="/reports/investments" onClick={() => setSidebarOpen(false)}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="1,12 5,7.5 9,9.5 15,3" />
            <polyline points="11,3 15,3 15,7" />
          </svg>
          Investments
        </SidebarNavLink>
        <SidebarNavLink to="/reports/retirement" onClick={() => setSidebarOpen(false)}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          >
            <circle cx="8" cy="8" r="6.5" />
            <polyline points="8,4.5 8,8.5 10.5,10" strokeLinejoin="round" />
          </svg>
          Retirement
        </SidebarNavLink>
        <SidebarNavLink to="/assets" onClick={() => setSidebarOpen(false)}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M1.5 7.5L8 2l6.5 5.5" />
            <path d="M3.5 6.5V14H6.5V10.5H9.5V14H12.5V6.5" />
          </svg>
          Real estate
        </SidebarNavLink>
        <SidebarNavLink to="/reports/cash-flow" onClick={() => setSidebarOpen(false)}>
          <svg
            width="15"
            height="15"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="8" cy="8" r="6.5" />
            <path d="M8 4.5v7M6 6.5a2 2 0 0 1 2-1.5h.5a1.5 1.5 0 0 1 0 3h-1a1.5 1.5 0 0 0 0 3H8a2 2 0 0 0 2-1.5" />
          </svg>
          Cash flow
        </SidebarNavLink>
      </nav>

      {/* Planning section */}
      <div style={{ marginTop: "20px" }}>
        <div
          style={{
            fontSize: "10px",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--faint)",
            padding: "0 12px",
            marginBottom: "4px",
          }}
        >
          Planning
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          <SidebarNavLink to="/fire" onClick={() => setSidebarOpen(false)}>
            FIRE
          </SidebarNavLink>
          <SidebarNavLink to="/debt" onClick={() => setSidebarOpen(false)}>
            Debt
          </SidebarNavLink>
          <SidebarNavLink to="/budgets" onClick={() => setSidebarOpen(false)}>
            Budgets
          </SidebarNavLink>
        </div>
      </div>

      {/* Footer: net worth */}
      <div
        style={{
          marginTop: "auto",
          padding: "14px 12px 4px",
          borderTop: "1px solid var(--bd)",
        }}
      >
        <div style={{ fontSize: "11px", color: "var(--faint)", letterSpacing: "0.04em" }}>
          Net worth
        </div>
        <div style={{ fontSize: "20px", fontWeight: 600, color: "var(--text)", marginTop: "3px" }}>
          {netWorth ? formatCurrency(netWorth) : "—"}
        </div>
      </div>
    </aside>
  )

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <ExportModal open={exportOpen} onClose={() => setExportOpen(false)} />

      {/* Sidebar — hidden on mobile */}
      <div className="hidden md:block">{sidebar}</div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "flex",
          }}
          onClick={() => setSidebarOpen(false)}
        >
          <div onClick={(e) => e.stopPropagation()}>{sidebar}</div>
          <div style={{ flex: 1, background: "rgba(0,0,0,0.5)" }} />
        </div>
      )}

      {/* Main area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Header */}
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 30px",
            borderBottom: "1px solid var(--bd)",
            background: "var(--bg)",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          {/* Left: hamburger (mobile) + household info */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              className="md:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--muted)",
                padding: "4px",
              }}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <line
                  x1="3"
                  y1="5"
                  x2="17"
                  y2="5"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
                <line
                  x1="3"
                  y1="10"
                  x2="17"
                  y2="10"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
                <line
                  x1="3"
                  y1="15"
                  x2="17"
                  y2="15"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </button>
            <div>
              <div style={{ fontSize: "19px", fontWeight: 600, color: "var(--text)" }}>
                {householdName ?? "HearthLedger"}
              </div>
              <div
                style={{
                  fontSize: "11px",
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: "var(--faint)",
                  marginTop: "2px",
                }}
              >
                As of {today}
                {accountCount !== null ? ` · ${accountCount} accounts` : ""}
              </div>
            </div>
          </div>

          {/* Right: range toggle + identity widget */}
          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {/* Range toggle */}
            <div
              style={{
                display: "flex",
                gap: "3px",
                background: "var(--toggle-off-bg)",
                padding: "3px",
                borderRadius: "9px",
              }}
            >
              {(["ytd", "1y", "all"] as Range[]).map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "7px",
                    fontSize: "12px",
                    fontWeight: 500,
                    border: "none",
                    cursor: "pointer",
                    background: range === r ? "var(--toggle-on-bg)" : "transparent",
                    color: range === r ? "var(--toggle-on-text)" : "var(--toggle-off-text)",
                    transition: "background 0.1s, color 0.1s",
                  }}
                >
                  {r === "ytd" ? "YTD" : r === "1y" ? "1Y" : "All"}
                </button>
              ))}
            </div>

            {/* Divider */}
            <div style={{ width: "1px", height: "28px", background: "var(--bd2)" }} />

            {/* Identity widget */}
            <div style={{ position: "relative" }} ref={userMenuRef}>
              <button
                aria-haspopup="true"
                aria-expanded={userMenuOpen}
                aria-label={`User menu: ${displayName}`}
                onClick={() => setUserMenuOpen((v) => !v)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "11px",
                  cursor: "pointer",
                  padding: "5px 12px 5px 5px",
                  borderRadius: "30px",
                  border: "1px solid var(--bd2)",
                  background: "none",
                }}
              >
                {/* Avatar */}
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "30px",
                    height: "30px",
                    borderRadius: "50%",
                    background: "var(--card)",
                    border: `2px solid ${roleRingColor}`,
                    fontSize: "11px",
                    fontWeight: 600,
                    color: roleRingColor,
                    flexShrink: 0,
                  }}
                >
                  {initials}
                </span>
                <div style={{ textAlign: "left" }}>
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "var(--text)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {firstName}
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--faint)", whiteSpace: "nowrap" }}>
                    {roleLabel}
                  </div>
                </div>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 20 20"
                  fill="none"
                  style={{ marginLeft: "2px", flexShrink: 0 }}
                >
                  <path
                    d="M6 8 L10 12 L14 8"
                    stroke="var(--faint)"
                    strokeWidth="1.7"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>

              {/* Dropdown */}
              {userMenuOpen && (
                <div
                  role="menu"
                  style={{
                    position: "absolute",
                    right: 0,
                    top: "calc(100% + 10px)",
                    width: "280px",
                    background: "var(--card)",
                    border: "1px solid var(--bd2)",
                    borderRadius: "14px",
                    boxShadow: "0 24px 60px rgba(0,0,0,.55)",
                    zIndex: 41,
                    overflow: "hidden",
                  }}
                >
                  {/* Current user card */}
                  <div style={{ padding: "18px", borderBottom: "1px solid var(--bd)" }}>
                    <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text)" }}>
                      {displayName}
                    </div>
                    {householdName && (
                      <div style={{ fontSize: "11.5px", color: "var(--label)", marginTop: "2px" }}>
                        {householdName}
                      </div>
                    )}
                  </div>

                  {/* Appearance toggle */}
                  <div
                    style={{
                      padding: "10px 16px",
                      borderBottom: "1px solid var(--bd)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <span style={{ fontSize: "12.5px", color: "var(--text3)" }}>Appearance</span>
                    <div
                      style={{
                        display: "flex",
                        gap: "3px",
                        background: "var(--toggle-off-bg)",
                        padding: "3px",
                        borderRadius: "9px",
                      }}
                    >
                      {(["dark", "light", "system"] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => setTheme(t)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: "7px",
                            fontSize: "11px",
                            border: "none",
                            cursor: "pointer",
                            background: theme === t ? "var(--toggle-on-bg)" : "transparent",
                            color: theme === t ? "var(--toggle-on-text)" : "var(--toggle-off-text)",
                          }}
                        >
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Settings links */}
                  <div style={{ padding: "6px 12px 8px" }}>
                    <DropdownLink to="/members" onClick={() => setUserMenuOpen(false)}>
                      Members & roles
                    </DropdownLink>
                    <DropdownLink to="/categories" onClick={() => setUserMenuOpen(false)}>
                      Categories
                    </DropdownLink>
                    <DropdownLink to="/reports/net-worth" onClick={() => setUserMenuOpen(false)}>
                      Net Worth report
                    </DropdownLink>
                    <DropdownLink to="/reports/spending" onClick={() => setUserMenuOpen(false)}>
                      Spending report
                    </DropdownLink>
                    <div style={{ height: "1px", background: "var(--bd)", margin: "6px 0" }} />
                    <button
                      onClick={() => {
                        setUserMenuOpen(false)
                        setExportOpen(true)
                      }}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        width: "100%",
                        padding: "8px",
                        borderRadius: "8px",
                        fontSize: "13px",
                        color: "var(--text3)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      Export
                    </button>
                    <DropdownLink to="/settings/exports" onClick={() => setUserMenuOpen(false)}>
                      Export history
                    </DropdownLink>
                    <DropdownLink to="/settings/imports" onClick={() => setUserMenuOpen(false)}>
                      Import history
                    </DropdownLink>
                    {isPrimary && (
                      <DropdownLink to="/settings/backups" onClick={() => setUserMenuOpen(false)}>
                        Backups
                      </DropdownLink>
                    )}
                    <div style={{ height: "1px", background: "var(--bd)", margin: "6px 0" }} />
                    <DropdownLink to="/settings/security" onClick={() => setUserMenuOpen(false)}>
                      Security log
                    </DropdownLink>
                    {isPrimary && (
                      <DropdownLink to="/settings/activity" onClick={() => setUserMenuOpen(false)}>
                        Activity log
                      </DropdownLink>
                    )}
                    <DropdownLink to="/settings/dashboard" onClick={() => setUserMenuOpen(false)}>
                      Dashboard layout
                    </DropdownLink>
                    <DropdownLink to="/settings/appearance" onClick={() => setUserMenuOpen(false)}>
                      Appearance settings
                    </DropdownLink>
                  </div>

                  {/* Logout */}
                  <div style={{ borderTop: "1px solid var(--bd)", padding: "6px 12px 10px" }}>
                    <button
                      onClick={handleLogout}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "8px",
                        borderRadius: "8px",
                        fontSize: "13px",
                        color: "var(--liab)",
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, padding: "24px 30px 40px" }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function DropdownLink({
  to,
  children,
  onClick,
}: {
  to: string
  children: React.ReactNode
  onClick?: () => void
}) {
  return (
    <Link
      to={to}
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        padding: "8px",
        borderRadius: "8px",
        fontSize: "13px",
        color: "var(--text3)",
        textDecoration: "none",
      }}
      onMouseEnter={(e) => {
        ;(e.currentTarget as HTMLElement).style.background = "var(--bd)"
      }}
      onMouseLeave={(e) => {
        ;(e.currentTarget as HTMLElement).style.background = "transparent"
      }}
    >
      {children}
    </Link>
  )
}
