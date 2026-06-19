import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { accountsApi } from "@/api/accounts"
import { membersApi } from "@/api/members"
import { propertiesApi } from "@/api/properties"
import { useAuth } from "@/hooks/useAuth"
import type { AccountResponse, AccountType, PropertyType } from "@/api/types"

const ASSET_TYPES: AccountType[] = [
  "checking",
  "savings",
  "investment_brokerage",
  "retirement_401k",
  "retirement_403b",
  "retirement_ira",
  "retirement_roth_ira",
  "pension",
  "hsa",
  "real_estate",
  "other_asset",
]
const LIABILITY_TYPES: AccountType[] = [
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "student_loan",
  "other_liability",
]

const ACCOUNT_LABELS: Record<AccountType, string> = {
  checking: "Checking",
  savings: "Savings",
  credit_card: "Credit Card",
  investment_brokerage: "Brokerage",
  retirement_401k: "401(k)",
  retirement_403b: "403(b)",
  retirement_ira: "IRA",
  retirement_roth_ira: "Roth IRA",
  pension: "Pension",
  hsa: "HSA",
  real_estate: "Real Estate",
  mortgage: "Mortgage",
  auto_loan: "Auto Loan",
  personal_loan: "Personal Loan",
  student_loan: "Student Loan",
  other_asset: "Other Asset",
  other_liability: "Other Liability",
}

function formatBalance(val: string | null): string {
  if (val === null) return "—"
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(val))
}

const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  primary_residence: "Primary Residence",
  rental: "Rental Property",
  vacation: "Vacation Home",
  commercial: "Commercial",
  land: "Land",
  other: "Other",
}

const createSchema = z.object({
  account_type: z.string().min(1, "Required"),
  nickname: z.string().min(1, "Required"),
  institution_name: z.string().optional(),
  account_number: z.string().optional(),
  owner_member_id: z.string().optional(),
  property_type: z.string().optional(),
})
type CreateForm = z.infer<typeof createSchema>

function AddAccountModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const isPrimary = useAuth((s) => s.role === "primary")
  const memberId = useAuth((s) => s.memberId)
  const { data: allMembers } = useQuery({ queryKey: ["members"], queryFn: membersApi.list })
  // Partners may only own accounts jointly or as themselves — same rule
  // AccountService.create enforces server-side; this just keeps the UI from
  // offering choices the API will reject with 403.
  const members = isPrimary ? allMembers : allMembers?.filter((m) => m.id === memberId)
  const [modalStep, setModalStep] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
  })

  const create = useMutation({
    mutationFn: async (data: CreateForm) => {
      const account = await accountsApi.create({
        account_type: data.account_type as AccountType,
        nickname: data.nickname,
        institution_name: data.institution_name || null,
        account_number: data.account_number || null,
        owner_member_id: data.owner_member_id || null,
      })
      if (data.account_type === "real_estate") {
        await propertiesApi.create({
          account_id: account.id,
          address: "",
          property_type: (data.property_type || "primary_residence") as PropertyType,
        })
      }
      return account
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      onClose()
    },
    onError: () => setError("Failed to create account."),
  })

  const selectedType = watch("account_type") as AccountType | undefined

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Add account</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-4">
          {modalStep === 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Account type</p>
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                    Assets
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {ASSET_TYPES.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => {
                          setValue("account_type", t)
                          setModalStep(1)
                        }}
                        className={`text-xs rounded-lg border px-2 py-2 text-left hover:bg-indigo-50 hover:border-indigo-300 transition-colors ${selectedType === t ? "border-indigo-500 bg-indigo-50" : "border-gray-200"}`}
                      >
                        {ACCOUNT_LABELS[t]}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                    Liabilities
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {LIABILITY_TYPES.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => {
                          setValue("account_type", t)
                          setModalStep(1)
                        }}
                        className={`text-xs rounded-lg border px-2 py-2 text-left hover:bg-indigo-50 hover:border-indigo-300 transition-colors ${selectedType === t ? "border-indigo-500 bg-indigo-50" : "border-gray-200"}`}
                      >
                        {ACCOUNT_LABELS[t]}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {modalStep === 1 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nickname</label>
                <input
                  {...register("nickname")}
                  placeholder="e.g. BofA Checking"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                {errors.nickname && (
                  <p className="mt-1 text-xs text-red-600">{errors.nickname.message}</p>
                )}
              </div>
              {selectedType === "real_estate" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Property type
                  </label>
                  <select
                    {...register("property_type")}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    defaultValue="primary_residence"
                  >
                    {(Object.entries(PROPERTY_TYPE_LABELS) as [PropertyType, string][]).map(
                      ([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ),
                    )}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Institution name
                </label>
                <input
                  {...register("institution_name")}
                  placeholder="e.g. Bank of America"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Account number
                </label>
                <input
                  {...register("account_number")}
                  placeholder="Optional"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </>
          )}

          {modalStep === 2 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Owner</label>
              <select
                {...register("owner_member_id")}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Joint account</option>
                {members?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {modalStep > 0 && (
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setModalStep((s) => s - 1)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Back
              </button>
              {modalStep < 2 ? (
                <button
                  type="button"
                  onClick={() => setModalStep((s) => s + 1)}
                  className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={create.isPending}
                  className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                  {create.isPending ? "Adding…" : "Add account"}
                </button>
              )}
            </div>
          )}
        </form>
      </div>
    </div>
  )
}

function AccountGroup({ title, accounts }: { title: string; accounts: AccountResponse[] }) {
  if (accounts.length === 0) return null
  return (
    <div>
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">{title}</h2>
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 mb-6">
        {accounts.map((a) => (
          <Link
            key={a.id}
            to="/accounts/$accountId/transactions"
            params={{ accountId: a.id }}
            className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 truncate">{a.nickname}</p>
              <p className="text-sm text-gray-500">
                {a.institution_name ?? ACCOUNT_LABELS[a.account_type]}
                {a.account_number_last4 && ` •••• ${a.account_number_last4}`}
              </p>
            </div>
            <div className="text-right">
              <p className="font-medium text-gray-900">{formatBalance(a.current_balance)}</p>
              {a.balance_as_of && <p className="text-xs text-gray-400">{a.balance_as_of}</p>}
            </div>
          </Link>
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

  const assets = accounts?.filter((a) => ASSET_TYPES.includes(a.account_type)) ?? []
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

      {showAdd && <AddAccountModal onClose={() => setShowAdd(false)} />}
    </div>
  )
}
