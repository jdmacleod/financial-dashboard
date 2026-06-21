import { useEffect, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { accountsApi } from "@/api/accounts"
import { membersApi } from "@/api/members"
import { propertiesApi } from "@/api/properties"
import { useAuth } from "@/hooks/useAuth"
import { ACCOUNT_LABELS, PROPERTY_TYPE_LABELS } from "@/lib/accountLabels"
import type { AccountType, PropertyType } from "@/api/types"

const ALL_ASSET_TYPES: AccountType[] = [
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
const ALL_LIABILITY_TYPES: AccountType[] = [
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "student_loan",
  "heloc",
  "other_liability",
]

const createSchema = z
  .object({
    account_type: z.string().min(1, "Required"),
    nickname: z.string().min(1, "Required"),
    institution_name: z.string().optional(),
    account_number: z.string().optional(),
    notes: z.string().optional(),
    owner_member_id: z.string().optional(),
    property_type: z.string().optional(),
    address: z.string().optional(),
    purchase_date: z.string().optional(),
    purchase_price: z.string().optional(),
    linked_mortgage_account_id: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.account_type === "real_estate" && !data.address?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Address is required for real estate accounts",
        path: ["address"],
      })
    }
  })
type CreateForm = z.infer<typeof createSchema>

interface AddAccountModalProps {
  onClose: () => void
  allowedTypes: AccountType[]
  label?: "account" | "asset"
}

// Steps: 0 = owner (multi-member only), 1 = type, 2 = details
const STEP_OWNER = 0
const STEP_TYPE = 1
const STEP_DETAILS = 2

export default function AddAccountModal({
  onClose,
  allowedTypes,
  label = "account",
}: AddAccountModalProps) {
  const labelCap = label === "asset" ? "Asset" : "Account"
  const queryClient = useQueryClient()
  const isPrimary = useAuth((s) => s.role === "primary")
  const memberId = useAuth((s) => s.memberId)
  const { data: allMembers } = useQuery({ queryKey: ["members"], queryFn: membersApi.list })
  const { data: existingAccounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.list,
  })

  const isMultiMember = (allMembers?.length ?? 0) > 1
  const members = isPrimary ? allMembers : allMembers?.filter((m) => m.id === memberId)
  const mortgageAccounts =
    existingAccounts?.filter((a) => a.account_type === "mortgage" && a.is_active) ?? []

  const assetTypes = allowedTypes.filter((t) => ALL_ASSET_TYPES.includes(t))
  const liabilityTypes = allowedTypes.filter((t) => ALL_LIABILITY_TYPES.includes(t))

  // Start at STEP_TYPE (safe for single-member); upgrade to STEP_OWNER once members load.
  const [modalStep, setModalStep] = useState(STEP_TYPE)
  const ownerStepInitialized = useRef(false)
  useEffect(() => {
    if (allMembers && !ownerStepInitialized.current) {
      ownerStepInitialized.current = true
      if (allMembers.length > 1) {
        setModalStep(STEP_OWNER)
      }
    }
  }, [allMembers])

  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { owner_member_id: "" },
  })

  const create = useMutation({
    mutationFn: async (data: CreateForm) => {
      const account = await accountsApi.create({
        account_type: data.account_type as AccountType,
        nickname: data.nickname,
        institution_name: data.institution_name || null,
        account_number: data.account_number || null,
        owner_member_id: data.owner_member_id || null,
        notes: data.notes || null,
      })
      if (data.account_type === "real_estate") {
        await propertiesApi.create({
          account_id: account.id,
          address: data.address || "",
          property_type: (data.property_type || "primary_residence") as PropertyType,
          purchase_date: data.purchase_date || null,
          purchase_price: data.purchase_price || null,
          linked_mortgage_account_id: data.linked_mortgage_account_id || null,
        })
      }
      return account
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      onClose()
    },
    onError: () => setError(`Failed to create ${label}.`),
  })

  const selectedType = watch("account_type") as AccountType | undefined

  const handleBack = () => {
    if (modalStep === STEP_DETAILS) {
      setModalStep(STEP_TYPE)
    } else if (modalStep === STEP_TYPE) {
      if (isMultiMember) {
        setModalStep(STEP_OWNER)
      } else {
        onClose()
      }
    } else if (modalStep === STEP_OWNER) {
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md bg-white rounded-xl shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Add {label}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-4">
          {/* Step 0: Owner */}
          {modalStep === STEP_OWNER && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-3">Who owns this {label}?</p>
              <div className="space-y-2">
                <label className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-indigo-50 hover:border-indigo-300 transition-colors has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50">
                  <input
                    type="radio"
                    {...register("owner_member_id")}
                    value=""
                    className="text-indigo-600"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Joint household</p>
                    <p className="text-xs text-gray-500">Shared by all household members</p>
                  </div>
                </label>
                {members?.map((m) => (
                  <label
                    key={m.id}
                    className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-indigo-50 hover:border-indigo-300 transition-colors has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50"
                  >
                    <input
                      type="radio"
                      {...register("owner_member_id")}
                      value={m.id}
                      className="text-indigo-600"
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{m.display_name}</p>
                      <p className="text-xs text-gray-500">
                        {m.role === "primary" ? "Primary member" : "Household member"}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex gap-3 mt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => setModalStep(STEP_TYPE)}
                  className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Step 1: Type selection */}
          {modalStep === STEP_TYPE && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">{labelCap} type</p>
              <div className="space-y-3">
                {assetTypes.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                      Assets
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      {assetTypes.map((t) => (
                        <button
                          key={t}
                          type="button"
                          onClick={() => {
                            setValue("account_type", t)
                            setModalStep(STEP_DETAILS)
                          }}
                          className={`text-xs rounded-lg border px-2 py-2 text-left hover:bg-indigo-50 hover:border-indigo-300 transition-colors ${selectedType === t ? "border-indigo-500 bg-indigo-50" : "border-gray-200"}`}
                        >
                          {ACCOUNT_LABELS[t]}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {liabilityTypes.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                      Liabilities
                    </p>
                    <div className="grid grid-cols-3 gap-2">
                      {liabilityTypes.map((t) => (
                        <button
                          key={t}
                          type="button"
                          onClick={() => {
                            setValue("account_type", t)
                            setModalStep(STEP_DETAILS)
                          }}
                          className={`text-xs rounded-lg border px-2 py-2 text-left hover:bg-indigo-50 hover:border-indigo-300 transition-colors ${selectedType === t ? "border-indigo-500 bg-indigo-50" : "border-gray-200"}`}
                        >
                          {ACCOUNT_LABELS[t]}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={handleBack}
                className="mt-4 w-full rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                {isMultiMember ? "Back" : "Cancel"}
              </button>
            </div>
          )}

          {/* Step 2: Details */}
          {modalStep === STEP_DETAILS && (
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
                <>
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
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Address <span className="text-red-500">*</span>
                    </label>
                    <input
                      {...register("address")}
                      placeholder="e.g. 123 Main St"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    {errors.address && (
                      <p className="mt-1 text-xs text-red-600">{errors.address.message}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Purchase date
                      </label>
                      <input
                        type="date"
                        {...register("purchase_date")}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Purchase price
                      </label>
                      <input
                        {...register("purchase_price")}
                        placeholder="e.g. 350000.00"
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>
                  </div>
                  {mortgageAccounts.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Linked mortgage{" "}
                        <span className="text-gray-400 font-normal">(optional)</span>
                      </label>
                      <select
                        {...register("linked_mortgage_account_id")}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">None</option>
                        {mortgageAccounts.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.nickname}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </>
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
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ownership notes <span className="text-gray-400 font-normal">(optional)</span>
                </label>
                <input
                  {...register("notes")}
                  placeholder="e.g. held in Smith Family Trust, JTWROS"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </>
          )}

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {modalStep === STEP_DETAILS && (
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleBack}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={create.isPending}
                className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                {create.isPending ? "Adding…" : `Add ${label}`}
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  )
}
