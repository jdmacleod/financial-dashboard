import { useState } from "react"
import { Link, Outlet, useNavigate } from "@tanstack/react-router"
import { useAuth } from "@/hooks/useAuth"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { ExportModal } from "@/components/app/ExportModal"

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
      activeProps={{
        className: "text-sm text-indigo-600 font-medium dark:text-indigo-400",
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

  const [reportsOpen, setReportsOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)

  async function handleLogout() {
    setUserMenuOpen(false)
    await logout()
    navigate({ to: "/login" })
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <ExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 relative">
        <div className="max-w-5xl mx-auto px-4 flex items-center gap-6 h-14">
          <Link
            to="/"
            className="font-semibold text-gray-900 hover:text-gray-700 dark:text-gray-100 dark:hover:text-gray-300"
          >
            HearthLedger
          </Link>
          <NavLink to="/">Dashboard</NavLink>
          <NavLink to="/accounts">Accounts</NavLink>
          <NavLink to="/assets">Assets</NavLink>
          <NavLink to="/budgets">Budgets</NavLink>

          {/* Reports dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setReportsOpen((v) => !v)
                setUserMenuOpen(false)
              }}
              className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 flex items-center gap-1"
            >
              Reports
              <span className="text-xs">▾</span>
            </button>
            {reportsOpen && (
              <div
                className="absolute top-full left-0 mt-1 w-44 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg py-1 z-50"
                onMouseLeave={() => setReportsOpen(false)}
              >
                <Link
                  to="/reports/net-worth"
                  onClick={() => setReportsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Net Worth
                </Link>
                <Link
                  to="/reports/cash-flow"
                  onClick={() => setReportsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Cash Flow
                </Link>
                <Link
                  to="/reports/spending"
                  onClick={() => setReportsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Spending
                </Link>
              </div>
            )}
          </div>

          <NavLink to="/fire">FIRE</NavLink>
          <NavLink to="/debt">Debt</NavLink>
          <NavLink to="/members">Members</NavLink>
          <NavLink to="/categories">Categories</NavLink>

          {/* Export button */}
          <button
            onClick={() => setExportOpen(true)}
            className="text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            Export
          </button>

          {/* User menu — identity + settings + logout */}
          <div className="relative ml-auto">
            <button
              aria-haspopup="true"
              aria-expanded={userMenuOpen}
              aria-label={`User menu: ${displayName}`}
              onClick={() => {
                setUserMenuOpen((v) => !v)
                setReportsOpen(false)
              }}
              onKeyDown={(e) => e.key === "Escape" && setUserMenuOpen(false)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
            >
              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-indigo-600 text-xs font-semibold text-white shrink-0">
                {initials}
              </span>
              <span className="hidden sm:inline truncate max-w-[120px]">{firstName}</span>
              <span className="text-xs">▾</span>
            </button>

            {userMenuOpen && (
              <div
                className="absolute top-full right-0 mt-1 w-56 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg py-1 z-50"
                onMouseLeave={() => setUserMenuOpen(false)}
              >
                {/* Identity header */}
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                  {householdName && (
                    <p
                      className="text-xs text-gray-500 dark:text-gray-400 truncate"
                      title={householdName}
                    >
                      {householdName}
                    </p>
                  )}
                  <p
                    className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate"
                    title={displayName}
                  >
                    {displayName}
                  </p>
                  {role && (
                    <p className="text-xs text-gray-400 dark:text-gray-500 capitalize">{role}</p>
                  )}
                </div>

                {/* Settings links */}
                <Link
                  to="/settings/security"
                  onClick={() => setUserMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Security Log
                </Link>
                {isPrimary && (
                  <Link
                    to="/settings/activity"
                    onClick={() => setUserMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    Activity Log
                  </Link>
                )}
                <Link
                  to="/settings/exports"
                  onClick={() => setUserMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Exports
                </Link>
                <Link
                  to="/settings/imports"
                  onClick={() => setUserMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Import History
                </Link>
                {isPrimary && (
                  <Link
                    to="/settings/backups"
                    onClick={() => setUserMenuOpen(false)}
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                  >
                    Backups
                  </Link>
                )}
                <Link
                  to="/settings/dashboard"
                  onClick={() => setUserMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Dashboard Layout
                </Link>
                <Link
                  to="/settings/appearance"
                  onClick={() => setUserMenuOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  Appearance
                </Link>

                {/* Logout */}
                <div className="border-t border-gray-100 dark:border-gray-700 mt-1 pt-1">
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                  >
                    Log out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>
      <Outlet />
    </div>
  )
}
