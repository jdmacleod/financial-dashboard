import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { accountsApi } from "@/api/accounts"
import { propertiesApi } from "@/api/properties"
import { pensionApi } from "@/api/pension"
import { snapshotsApi } from "@/api/snapshots"
import { ACCOUNT_LABELS, PROPERTY_TYPE_LABELS } from "@/lib/accountLabels"
import { formatCurrencyOrDash } from "@/lib/formatters"
import { useAuth } from "@/hooks/useAuth"
import AddAccountModal from "@/components/app/AddAccountModal"
import ArchiveAccountModal from "@/components/app/ArchiveAccountModal"
import type {
  AccountResponse,
  AccountType,
  PensionAccountResponse,
  PropertyResponse,
} from "@/api/types"

const INVESTMENT_TYPES: AccountType[] = [
  "investment_brokerage",
  "retirement_401k",
  "retirement_403b",
  "retirement_ira",
  "retirement_roth_ira",
  "hsa",
]

// Types shown in the Add Asset modal — valuation-based only.
const ASSETS_PAGE_TYPES: AccountType[] = ["real_estate", "pension", ...INVESTMENT_TYPES]

function pensionPV(monthlyBenefit: string | null): string {
  if (!monthlyBenefit) return "—"
  const pv = (Number(monthlyBenefit) * 12) / 0.04
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(pv)
}

// Three-dot menu button — appears on hover
function OptionsMenu({ onArchive }: { onArchive: () => void }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setOpen((o) => !o)
        }}
        aria-label="Account options"
        className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        ···
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-7 z-50 w-44 bg-white rounded-lg border border-gray-200 shadow-lg py-1">
            <button
              onClick={() => {
                setOpen(false)
                onArchive()
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              Archive account
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// UpdateValueModal — creates a snapshot for an investment account
const updateValueSchema = z.object({
  balance: z.string().regex(/^\d+(\.\d{1,4})?$/, "Enter a valid amount (up to 4 decimal places)"),
  snapshot_date: z.string().min(1, "Date required"),
})
type UpdateValueForm = z.infer<typeof updateValueSchema>

function UpdateValueModal({ account, onClose }: { account: AccountResponse; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const today = new Date().toISOString().slice(0, 10)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<UpdateValueForm>({
    resolver: zodResolver(updateValueSchema),
    defaultValues: { snapshot_date: today },
  })

  const submit = useMutation({
    mutationFn: (data: UpdateValueForm) =>
      snapshotsApi.create(account.id, {
        balance: data.balance,
        snapshot_date: data.snapshot_date,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      queryClient.invalidateQueries({ queryKey: ["reports", "net-worth"] })
      onClose()
    },
    onError: () => setError("Failed to save value. Please try again."),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Update value</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{account.nickname}</p>
        <form onSubmit={handleSubmit((d) => submit.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Balance ($)</label>
            <input
              {...register("balance")}
              placeholder="e.g. 12500.00"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.balance && (
              <p className="mt-1 text-xs text-red-600">{errors.balance.message}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">As of date</label>
            <input
              type="date"
              {...register("snapshot_date")}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.snapshot_date && (
              <p className="mt-1 text-xs text-red-600">{errors.snapshot_date.message}</p>
            )}
          </div>
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submit.isPending}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {submit.isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Real Estate section
function RealEstateCard({ account }: { account: AccountResponse }) {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [archiving, setArchiving] = useState(false)
  const { data: property, isLoading: propertyLoading } = useQuery<PropertyResponse | null>({
    queryKey: ["property-by-account", account.id],
    queryFn: () => propertiesApi.getByAccountId(account.id),
  })

  const subtitle = propertyLoading
    ? "Loading…"
    : property
      ? `${PROPERTY_TYPE_LABELS[property.property_type] ?? property.property_type} · ${property.address}`
      : "No property record"

  return (
    <>
      <div className="flex items-center gap-2 px-4 py-3 hover:bg-gray-50 transition-colors group">
        <Link
          to="/properties/$propertyId"
          params={{ propertyId: property?.id ?? "" }}
          className={`flex flex-1 min-w-0 items-center gap-4 ${!property ? "pointer-events-none" : ""}`}
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">{account.nickname}</p>
            <p className="text-sm text-gray-500">{subtitle}</p>
          </div>
          <div className="text-right">
            <p className="font-medium text-gray-900">
              {property
                ? formatCurrencyOrDash(property.current_estimated_value)
                : formatCurrencyOrDash(account.current_balance)}
            </p>
            {property?.current_value_as_of && (
              <p className="text-xs text-gray-400">as of {property.current_value_as_of}</p>
            )}
          </div>
        </Link>
        {isPrimary && <OptionsMenu onArchive={() => setArchiving(true)} />}
      </div>
      {archiving && <ArchiveAccountModal account={account} onClose={() => setArchiving(false)} />}
    </>
  )
}

function RealEstateSection({ accounts }: { accounts: AccountResponse[] }) {
  return (
    <div className="mb-8">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Real Estate
      </h2>
      {accounts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 px-4 py-8 text-center text-gray-400">
          <p className="text-sm mb-1">No properties yet</p>
          <p className="text-xs">Add a real estate account to get started.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {accounts.map((a) => (
            <RealEstateCard key={a.id} account={a} />
          ))}
        </div>
      )}
    </div>
  )
}

// Pension section
function PensionCard({ account }: { account: AccountResponse }) {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [archiving, setArchiving] = useState(false)
  const { data: pension } = useQuery<PensionAccountResponse>({
    queryKey: ["pension-by-account", account.id],
    queryFn: () => pensionApi.get(account.id),
  })

  return (
    <>
      <div className="flex items-center gap-2 px-4 py-3 hover:bg-gray-50 transition-colors group">
        <Link
          to="/accounts/$accountId/pension"
          params={{ accountId: account.id }}
          className="flex flex-1 min-w-0 items-center gap-4"
        >
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate">{account.nickname}</p>
            <p className="text-sm text-gray-500">
              {pension?.plan_name ?? "Pension"}
              {pension && (
                <span
                  className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${pension.is_vested ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"}`}
                >
                  {pension.is_vested ? "Vested" : "Unvested"}
                </span>
              )}
            </p>
          </div>
          <div className="text-right">
            <p className="font-medium text-gray-900">
              {pensionPV(pension?.monthly_benefit_estimate ?? null)}
            </p>
            <p className="text-xs text-gray-400">~est. PV (4% discount)</p>
          </div>
        </Link>
        {isPrimary && <OptionsMenu onArchive={() => setArchiving(true)} />}
      </div>
      {archiving && <ArchiveAccountModal account={account} onClose={() => setArchiving(false)} />}
    </>
  )
}

function PensionSection({ accounts }: { accounts: AccountResponse[] }) {
  return (
    <div className="mb-8">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Pensions</h2>
      {accounts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 px-4 py-8 text-center text-gray-400">
          <p className="text-sm mb-1">No pension accounts yet</p>
          <p className="text-xs">Add a pension account to get started.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {accounts.map((a) => (
            <PensionCard key={a.id} account={a} />
          ))}
        </div>
      )}
    </div>
  )
}

// Investments section
function InvestmentRow({
  account,
  onUpdateValue,
}: {
  account: AccountResponse
  onUpdateValue: (a: AccountResponse) => void
}) {
  const isPrimary = useAuth((s) => s.role === "primary")
  const [archiving, setArchiving] = useState(false)

  return (
    <>
      <div className="flex items-center gap-2 px-4 py-3 group">
        <Link
          to="/accounts/$accountId/transactions"
          params={{ accountId: account.id }}
          className="flex-1 min-w-0 hover:text-indigo-600 transition-colors"
        >
          <p className="font-medium text-gray-900 truncate">{account.nickname}</p>
          <p className="text-sm text-gray-500">
            {account.institution_name ?? ACCOUNT_LABELS[account.account_type]}
            {account.account_number_last4 && ` •••• ${account.account_number_last4}`}
          </p>
        </Link>
        <div className="text-right mr-2">
          <p className="font-medium text-gray-900">
            {formatCurrencyOrDash(account.current_balance)}
          </p>
          {account.balance_as_of && (
            <p className="text-xs text-gray-400">as of {account.balance_as_of}</p>
          )}
        </div>
        <button
          onClick={() => onUpdateValue(account)}
          className="text-xs rounded-lg border border-gray-300 px-3 py-1.5 text-gray-600 hover:bg-gray-50 hover:border-gray-400 transition-colors whitespace-nowrap"
        >
          Update value
        </button>
        {isPrimary && <OptionsMenu onArchive={() => setArchiving(true)} />}
      </div>
      {archiving && <ArchiveAccountModal account={account} onClose={() => setArchiving(false)} />}
    </>
  )
}

function InvestmentsSection({
  accounts,
  onUpdateValue,
}: {
  accounts: AccountResponse[]
  onUpdateValue: (a: AccountResponse) => void
}) {
  return (
    <div className="mb-8">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
        Investments
      </h2>
      {accounts.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 px-4 py-8 text-center text-gray-400">
          <p className="text-sm mb-1">No investment accounts yet</p>
          <p className="text-xs">Add a brokerage, 401(k), IRA, or HSA account to get started.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {accounts.map((a) => (
            <InvestmentRow key={a.id} account={a} onUpdateValue={onUpdateValue} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function Assets() {
  const {
    data: accounts,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  })

  const [updateTarget, setUpdateTarget] = useState<AccountResponse | null>(null)
  const [showAdd, setShowAdd] = useState(false)

  const realEstate = accounts?.filter((a) => a.account_type === "real_estate") ?? []
  const pensions = accounts?.filter((a) => a.account_type === "pension") ?? []
  const investments = accounts?.filter((a) => INVESTMENT_TYPES.includes(a.account_type)) ?? []

  if (isLoading) return <div className="p-8 text-gray-500">Loading assets…</div>
  if (error) return <div className="p-8 text-red-600">Failed to load assets.</div>

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Assets</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          Add asset
        </button>
      </div>

      <RealEstateSection accounts={realEstate} />
      <PensionSection accounts={pensions} />
      <InvestmentsSection accounts={investments} onUpdateValue={setUpdateTarget} />

      {updateTarget && (
        <UpdateValueModal account={updateTarget} onClose={() => setUpdateTarget(null)} />
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
