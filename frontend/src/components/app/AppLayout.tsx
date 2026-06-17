import { Outlet } from "@tanstack/react-router"

export function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 flex items-center gap-6 h-14">
          <span className="font-semibold text-gray-900">HearthLedger</span>
          <a href="/" className="text-sm text-gray-600 hover:text-gray-900">
            Dashboard
          </a>
          <a href="/accounts" className="text-sm text-gray-600 hover:text-gray-900">
            Accounts
          </a>
          <a href="/members" className="text-sm text-gray-600 hover:text-gray-900">
            Members
          </a>
        </div>
      </nav>
      <Outlet />
    </div>
  )
}
