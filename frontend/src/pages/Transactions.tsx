import { useState } from "react"
import { useParams, Link } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil, Trash2 } from "lucide-react"
import { transactionsApi } from "@/api/transactions"
import { categoriesApi } from "@/api/categories"
import { accountsApi } from "@/api/accounts"
import { propertiesApi } from "@/api/properties"
import { pensionApi } from "@/api/pension"
import { ImportModal } from "@/components/app/ImportModal"
import { AddTransactionModal } from "@/components/app/AddTransactionModal"
import { EditTransactionModal } from "@/components/app/EditTransactionModal"
import { HistoryPanel } from "@/components/app/HistoryPanel"
import { formatCurrency, formatDate } from "@/lib/formatters"
import { INVESTMENT_ACCOUNT_TYPES } from "@/lib/accountTypes"
import type { CategoryResponse, TransactionResponse } from "@/api/types"

const PAGE_SIZE = 50

function CategoryBadge({
  transaction,
  categories,
  onChange,
}: {
  transaction: TransactionResponse
  categories: CategoryResponse[]
  onChange: (categoryId: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const category = categories.find((c) => c.id === transaction.category_id)

  if (editing) {
    return (
      <select
        autoFocus
        value={transaction.category_id ?? ""}
        onChange={(e) => {
          onChange(e.target.value)
          setEditing(false)
        }}
        onBlur={() => setEditing(false)}
        className="rounded-md border border-gray-300 px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="">Uncategorized</option>
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
    )
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium hover:opacity-80 transition-opacity"
      style={{
        backgroundColor: category ? `${category.color_hex}1a` : "#f3f4f6",
        color: category ? category.color_hex : "#6b7280",
      }}
    >
      {category?.name ?? "Uncategorized"}
    </button>
  )
}

function DeleteConfirmDialog({
  onConfirm,
  onCancel,
  isPending,
  hasError,
}: {
  onConfirm: () => void
  onCancel: () => void
  isPending: boolean
  hasError: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6">
        <h2 className="text-lg font-semibold mb-2">Delete transaction?</h2>
        <p className="text-sm text-gray-600 mb-4">This cannot be undone.</p>
        {hasError && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            Failed to delete. Please try again.
          </p>
        )}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-60"
          >
            {isPending ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Transactions() {
  const { accountId } = useParams({ strict: false }) as { accountId: string }
  const queryClient = useQueryClient()
  const [unreviewedOnly, setUnreviewedOnly] = useState(false)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [bulkCategoryId, setBulkCategoryId] = useState("")
  const [showImport, setShowImport] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [editingTransaction, setEditingTransaction] = useState<TransactionResponse | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null)

  const { data: account } = useQuery({
    queryKey: ["accounts", accountId],
    queryFn: () => accountsApi.get(accountId),
  })

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  })

  const {
    data: page_,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["transactions", accountId, { unreviewedOnly, search, page }],
    queryFn: () =>
      transactionsApi.list(accountId, {
        is_reviewed: unreviewedOnly ? false : undefined,
        search: search || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
  })

  const updateCategory = useMutation({
    mutationFn: ({ id, categoryId }: { id: string; categoryId: string }) =>
      transactionsApi.update(id, { category_id: categoryId || null }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["transactions", accountId] }),
  })

  const bulkCategorize = useMutation({
    mutationFn: () =>
      transactionsApi.bulkCategorize(accountId, Array.from(selected), bulkCategoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", accountId] })
      setSelected(new Set())
      setBulkCategoryId("")
    },
  })

  const deleteTransaction = useMutation({
    mutationFn: (id: string) => transactionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions", accountId] })
      setDeletingId(null)
    },
  })

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const transactions = page_?.items ?? []
  const totalPages = page_ ? Math.max(1, Math.ceil(page_.total / PAGE_SIZE)) : 1
  const accountType = account?.account_type
  const isInvestmentAccount = accountType ? INVESTMENT_ACCOUNT_TYPES.includes(accountType) : false
  const isRealEstateAccount = accountType === "real_estate"
  const isPensionAccount = accountType === "pension"

  const { data: property } = useQuery({
    queryKey: ["accounts", accountId, "property"],
    queryFn: () => propertiesApi.getByAccountId(accountId),
    enabled: isRealEstateAccount,
    retry: false,
  })

  const { data: pension } = useQuery({
    queryKey: ["accounts", accountId, "pension"],
    queryFn: () => pensionApi.get(accountId),
    enabled: isPensionAccount,
    retry: false,
  })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">{account?.nickname ?? "Transactions"}</h1>
          <p className="text-sm text-gray-500">Transactions</p>
        </div>
        <div className="flex items-center gap-2">
          {!isRealEstateAccount && !isPensionAccount && (
            <button
              onClick={() => setShowAdd(true)}
              className="rounded-lg border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 transition-colors"
            >
              New entry
            </button>
          )}
          {!isPensionAccount && (
            <button
              onClick={() => setShowImport(true)}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              Import
            </button>
          )}
          {isRealEstateAccount && property && (
            <Link
              to="/properties/$propertyId"
              params={{ propertyId: String(property.id) }}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              Property details →
            </Link>
          )}
          {isPensionAccount && (
            <Link
              to="/accounts/$accountId/pension"
              params={{ accountId }}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
            >
              Edit pension details →
            </Link>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => {
            setUnreviewedOnly((v) => !v)
            setPage(1)
          }}
          className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
            unreviewedOnly
              ? "bg-indigo-600 border-indigo-600 text-white"
              : "border-gray-300 text-gray-600 hover:bg-gray-50"
          }`}
        >
          Unreviewed
        </button>
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          placeholder="Search payee…"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {selected.size > 0 && (
        <div className="flex items-center gap-3 mb-4 rounded-lg bg-indigo-50 border border-indigo-200 px-3 py-2">
          <span className="text-sm text-indigo-900">{selected.size} selected</span>
          <select
            value={bulkCategoryId}
            onChange={(e) => setBulkCategoryId(e.target.value)}
            className="rounded-md border border-indigo-300 px-2 py-1 text-sm"
          >
            <option value="">Choose category…</option>
            {categories?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => bulkCategorize.mutate()}
            disabled={!bulkCategoryId || bulkCategorize.isPending}
            className="rounded-md bg-indigo-600 px-3 py-1 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            Apply
          </button>
          <button
            onClick={() => setSelected(new Set())}
            className="text-sm text-indigo-700 hover:text-indigo-900"
          >
            Clear
          </button>
        </div>
      )}

      {isPensionAccount && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Defined Benefit Summary</h2>
          {pension ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Plan name</span>
                <span className="text-sm font-medium text-gray-900">
                  {pension.plan_name ?? "—"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Monthly benefit</span>
                <span className="text-sm font-medium text-gray-900">
                  {pension.monthly_benefit_estimate
                    ? formatCurrency(pension.monthly_benefit_estimate) + " / mo"
                    : "—"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Eligibility</span>
                <span className="text-sm font-medium text-gray-900">
                  {pension.eligibility_age != null ? `Age ${pension.eligibility_age}` : ""}
                  {pension.eligibility_age != null && pension.eligibility_date ? " · " : ""}
                  {pension.eligibility_date ?? (pension.eligibility_age == null ? "—" : "")}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Vested</span>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    pension.is_vested
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {pension.is_vested ? "Vested" : "Not vested"}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-4 text-gray-400">
              <p className="text-sm mb-3">No pension details recorded yet.</p>
              <Link
                to="/accounts/$accountId/pension"
                params={{ accountId }}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
              >
                Add pension details →
              </Link>
            </div>
          )}
        </div>
      )}

      {isRealEstateAccount && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 flex items-center justify-between">
          <p className="text-sm text-blue-800">
            This is a real estate account. Transactions below reflect property-related expenses.
          </p>
          {property && (
            <Link
              to="/properties/$propertyId"
              params={{ propertyId: String(property.id) }}
              className="text-sm font-medium text-blue-700 hover:text-blue-900 whitespace-nowrap ml-4"
            >
              Track this property →
            </Link>
          )}
        </div>
      )}

      {isLoading && <div className="text-gray-500">Loading transactions…</div>}
      {error && <div className="text-red-600">Failed to load transactions.</div>}

      {!isLoading && !error && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {transactions.map((t) => (
            <div key={t.id}>
              <div className="flex items-center gap-3 px-4 py-3">
                <input
                  type="checkbox"
                  checked={selected.has(t.id)}
                  onChange={() => toggleSelected(t.id)}
                  className="rounded border-gray-300"
                />
                <div className="w-20 shrink-0 text-xs text-gray-500">
                  {formatDate(t.transaction_date)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {t.payee_normalized ?? t.payee_raw ?? "—"}
                  </p>
                  {t.memo && <p className="text-xs text-gray-400 truncate">{t.memo}</p>}
                </div>
                <div className="flex items-center gap-2">
                  {t.real_estate_property_id && (
                    <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                      Property
                    </span>
                  )}
                  {categories && (
                    <CategoryBadge
                      transaction={t}
                      categories={categories}
                      onChange={(categoryId) => updateCategory.mutate({ id: t.id, categoryId })}
                    />
                  )}
                </div>
                <div
                  className={`w-24 text-right text-sm font-medium ${
                    Number(t.amount) < 0 ? "text-red-600" : "text-emerald-600"
                  }`}
                >
                  {formatCurrency(t.amount)}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => setEditingTransaction(t)}
                    className="p-1 text-gray-400 hover:text-indigo-600 transition-colors"
                    title="Edit transaction"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => setDeletingId(t.id)}
                    className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                    title="Delete transaction"
                  >
                    <Trash2 size={14} />
                  </button>
                  <button
                    onClick={() => setExpandedHistory((prev) => (prev === t.id ? null : t.id))}
                    className="text-xs text-gray-400 hover:text-gray-600"
                    title="View history"
                  >
                    {expandedHistory === t.id ? "▲" : "▾"}
                  </button>
                </div>
              </div>
              {expandedHistory === t.id && (
                <div className="px-4 pb-3">
                  <HistoryPanel entityType="transaction" entityId={t.id} />
                </div>
              )}
            </div>
          ))}
          {transactions.length === 0 && (
            <div className="px-4 py-10 text-center">
              {isInvestmentAccount ? (
                <>
                  <p className="text-gray-400 mb-3">
                    No transactions recorded yet. Add your first entry →
                  </p>
                  <button
                    onClick={() => setShowAdd(true)}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                  >
                    New entry
                  </button>
                </>
              ) : (
                <>
                  <p className="text-gray-400 mb-3">
                    No transactions yet. Import a file or add one manually.
                  </p>
                  <div className="flex items-center justify-center gap-2">
                    <button
                      onClick={() => setShowImport(true)}
                      className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                    >
                      Import
                    </button>
                    <button
                      onClick={() => setShowAdd(true)}
                      className="rounded-lg border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 transition-colors"
                    >
                      New entry
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {showImport && <ImportModal accountId={accountId} onClose={() => setShowImport(false)} />}

      {showAdd && accountType && categories && (
        <AddTransactionModal
          accountId={accountId}
          accountType={accountType}
          categories={categories}
          onClose={() => setShowAdd(false)}
        />
      )}

      {editingTransaction && categories && (
        <EditTransactionModal
          transaction={editingTransaction}
          categories={categories}
          onClose={() => setEditingTransaction(null)}
        />
      )}

      {deletingId && (
        <DeleteConfirmDialog
          onConfirm={() => deleteTransaction.mutate(deletingId)}
          onCancel={() => setDeletingId(null)}
          isPending={deleteTransaction.isPending}
          hasError={deleteTransaction.isError}
        />
      )}
    </div>
  )
}
