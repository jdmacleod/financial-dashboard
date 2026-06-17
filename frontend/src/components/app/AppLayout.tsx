import { useState } from "react"
import { Link, Outlet } from "@tanstack/react-router"
import { useAuth } from "@/hooks/useAuth"
import { ExportModal } from "@/components/app/ExportModal"

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="text-sm text-gray-600 hover:text-gray-900"
      activeProps={{ className: "text-sm text-indigo-600 font-medium" }}
    >
      {children}
    </Link>
  )
}

export function AppLayout() {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [reportsOpen, setReportsOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      <ExportModal open={exportOpen} onClose={() => setExportOpen(false)} />
      <nav className="bg-white border-b border-gray-200 relative">
        <div className="max-w-5xl mx-auto px-4 flex items-center gap-6 h-14">
          <Link to="/" className="font-semibold text-gray-900 hover:text-gray-700">
            HearthLedger
          </Link>
          <NavLink to="/">Dashboard</NavLink>
          <NavLink to="/accounts">Accounts</NavLink>
          <NavLink to="/budgets">Budgets</NavLink>

          {/* Reports dropdown */}
          <div className="relative">
            <button
              onClick={() => {
                setReportsOpen((v) => !v)
                setSettingsOpen(false)
              }}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              Reports
              <span className="text-xs">▾</span>
            </button>
            {reportsOpen && (
              <div
                className="absolute top-full left-0 mt-1 w-44 bg-white rounded-xl border border-gray-200 shadow-lg py-1 z-50"
                onMouseLeave={() => setReportsOpen(false)}
              >
                <Link
                  to="/reports/net-worth"
                  onClick={() => setReportsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Net Worth
                </Link>
                <Link
                  to="/reports/cash-flow"
                  onClick={() => setReportsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Cash Flow
                </Link>
                <Link
                  to="/reports/spending"
                  onClick={() => setReportsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
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
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Export
          </button>

          {/* Settings dropdown */}
          <div className="relative ml-auto">
            <button
              onClick={() => {
                setSettingsOpen((v) => !v)
                setReportsOpen(false)
              }}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
            >
              Settings
              <span className="text-xs">▾</span>
            </button>
            {settingsOpen && (
              <div
                className="absolute top-full right-0 mt-1 w-44 bg-white rounded-xl border border-gray-200 shadow-lg py-1 z-50"
                onMouseLeave={() => setSettingsOpen(false)}
              >
                <Link
                  to="/settings/security"
                  onClick={() => setSettingsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Security Log
                </Link>
                {isPrimary && (
                  <Link
                    to="/settings/activity"
                    onClick={() => setSettingsOpen(false)}
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    Activity Log
                  </Link>
                )}
                <Link
                  to="/settings/exports"
                  onClick={() => setSettingsOpen(false)}
                  className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Exports
                </Link>
              </div>
            )}
          </div>
        </div>
      </nav>
      <Outlet />
    </div>
  )
}
