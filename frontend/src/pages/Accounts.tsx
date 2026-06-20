import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery } from "@tanstack/react-query"
import { accountsApi } from "@/api/accounts"
import { useAuth } from "@/hooks/useAuth"
import { ACCOUNT_LABELS } from "@/lib/accountLabels"
import { formatCurrency } from "@/lib/formatters"
import AddAccountModal from "@/components/app/AddAccountModal"
import ArchiveAccountModal from "@/components/app/ArchiveAccountModal"
import type { AccountResponse, AccountType } from "@/api/types"

// Types shown in the Accounts list — transaction-based only.
// Valuation-based types (RE, pension, investment) appear on the Assets page.
const DISPLAY_ASSET_TYPES: AccountType[] = ["checking", "savings", "other_asset"]
const LIABILITY_TYPES: AccountType[] = [
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "student_loan",
  "other_liability",
]

// Types available in the Add Account modal on this page.
const ACCOUNTS_PAGE_TYPES: AccountType[] = [
  "checking",
  "savings",
  "other_asset",
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "student_loan",
  "other_liability",
]

function AccountRow({ account }: { account: AccountResponse }) {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [menuOpen, setMenuOpen] = useState(false)
  const [archiving, setArchiving] = useState(false)

  // All accounts on this page are transaction-based. Null balance = no transactions yet = $0.00.
  const balance = formatCurrency(account.current_balance ?? "0")

  return (
    <>
      <div className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors group">
        <Link
          to="/accounts/$accountId/transactions"
          params={{ accountId: account.id }}
          className="flex-1 min-w-0"
        >
          <p className="font-medium text-gray-900 truncate">{account.nickname}</p>
          <p className="text-sm text-gray-500">
            {account.institution_name ?? ACCOUNT_LABELS[account.account_type]}
            {account.account_number_last4 && ` •••• ${account.account_number_last4}`}
          </p>
        </Link>
        <div className="text-right">
          <p className="font-medium text-gray-900">{balance}</p>
          {account.balance_as_of && (
            <p className="text-xs text-gray-400">{account.balance_as_of}</p>
          )}
        </div>
        {isPrimary && (
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation()
                setMenuOpen((o) => !o)
              }}
              aria-label={`Account options for ${account.nickname}`}
              className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              ···
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-7 z-50 w-44 bg-white rounded-lg border border-gray-200 shadow-lg py-1">
                  <button
                    onClick={() => {
                      setMenuOpen(false)
                      setArchiving(true)
                    }}
                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    Archive account
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
      {archiving && <ArchiveAccountModal account={account} onClose={() => setArchiving(false)} />}
    </>
  )
}

function AccountGroup({ title, accounts }: { title: string; accounts: AccountResponse[] }) {
  if (accounts.length === 0) return null
  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{title}</h2>
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 mb-6">
        {accounts.map((a) => (
          <AccountRow key={a.id} account={a} />
        ))}
      </div>
    </div>
  )
}

export default function Accounts() {
  const {
    data: accounts,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  })
  const [showAdd, setShowAdd] = useState(false)

  const assets = accounts?.filter((a) => DISPLAY_ASSET_TYPES.includes(a.account_type)) ?? []
  const liabilities = accounts?.filter((a) => LIABILITY_TYPES.includes(a.account_type)) ?? []

  if (isLoading) return <div className="p-8 text-gray-500">Loading accounts…</div>
  if (error) return <div className="p-8 text-red-600">Failed to load accounts.</div>

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Accounts</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          Add account
        </button>
      </div>

      <AccountGroup title="Assets" accounts={assets} />
      <AccountGroup title="Liabilities" accounts={liabilities} />

      {accounts?.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg mb-2">No accounts yet</p>
          <p className="text-sm">Add your first account to get started.</p>
        </div>
      )}

      {showAdd && (
        <AddAccountModal allowedTypes={ACCOUNTS_PAGE_TYPES} onClose={() => setShowAdd(false)} />
      )}
    </div>
  )
}
