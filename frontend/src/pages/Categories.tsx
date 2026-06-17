import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { categoriesApi } from "@/api/categories"
import { ApiError } from "@/api/client"
import type { CategoryResponse } from "@/api/types"

const createSchema = z.object({
  name: z.string().min(1, "Name is required"),
  color_hex: z.string().regex(/^#[0-9a-fA-F]{6}$/, "Must be a hex color like #4f46e5"),
  icon: z.string().optional(),
  is_income: z.boolean(),
})
type CreateForm = z.infer<typeof createSchema>

function CategoryRow({
  category,
  onUpdate,
  onDelete,
}: {
  category: CategoryResponse
  onUpdate: (data: { name?: string; color_hex?: string; icon?: string | null }) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(category.name)
  const [colorHex, setColorHex] = useState(category.color_hex)
  const [icon, setIcon] = useState(category.icon ?? "")

  if (editing) {
    return (
      <div className="flex items-center gap-2 px-4 py-2">
        <input
          type="color"
          value={colorHex}
          onChange={(e) => setColorHex(e.target.value)}
          className="h-8 w-8 rounded border border-gray-300"
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-2 py-1 text-sm"
        />
        <input
          value={icon}
          onChange={(e) => setIcon(e.target.value)}
          placeholder="icon"
          className="w-20 rounded-lg border border-gray-300 px-2 py-1 text-sm"
        />
        <button
          onClick={() => {
            onUpdate({ name, color_hex: colorHex, icon: icon || null })
            setEditing(false)
          }}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          Save
        </button>
        <button
          onClick={() => setEditing(false)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2">
      <span
        className="inline-block h-3 w-3 rounded-full shrink-0"
        style={{ backgroundColor: category.color_hex }}
      />
      <span className="flex-1 text-sm text-gray-900">{category.name}</span>
      {category.is_system && <span className="text-xs text-gray-400">System category</span>}
      {!category.is_system && (
        <>
          <button
            onClick={() => setEditing(true)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Rename
          </button>
          <button onClick={onDelete} className="text-sm text-red-500 hover:text-red-700">
            Delete
          </button>
        </>
      )}
    </div>
  )
}

function AddCategoryForm({ isIncome, onSuccess }: { isIncome: boolean; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
    defaultValues: { name: "", color_hex: "#888888", icon: "", is_income: isIncome },
  })

  const create = useMutation({
    mutationFn: (data: CreateForm) =>
      categoriesApi.create({ ...data, icon: data.icon || null, is_income: isIncome }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] })
      reset({ name: "", color_hex: "#888888", icon: "", is_income: isIncome })
      onSuccess()
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : "Failed to create category.")
    },
  })

  return (
    <form
      onSubmit={handleSubmit((data) => create.mutate(data))}
      className="flex items-center gap-2 px-4 py-3 bg-gray-50"
    >
      <input
        type="color"
        {...register("color_hex")}
        defaultValue="#888888"
        className="h-8 w-8 rounded border border-gray-300"
      />
      <input
        {...register("name")}
        placeholder="New category name"
        className="flex-1 rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
      />
      <input
        {...register("icon")}
        placeholder="icon (optional)"
        className="w-32 rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
      />
      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
      >
        Add
      </button>
      {(errors.name || errors.color_hex || error) && (
        <span className="text-xs text-red-600">
          {errors.name?.message ?? errors.color_hex?.message ?? error}
        </span>
      )}
    </form>
  )
}

function CategoryGroup({ title, categories }: { title: string; categories: CategoryResponse[] }) {
  const queryClient = useQueryClient()
  const isIncome = title === "Income"

  const update = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string
      data: { name?: string; color_hex?: string; icon?: string | null }
    }) => categoriesApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  })

  const remove = useMutation({
    mutationFn: (id: string) => categoriesApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  })

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-700">{title}</h2>
      </div>
      <div className="divide-y divide-gray-100">
        {categories.map((c) => (
          <CategoryRow
            key={c.id}
            category={c}
            onUpdate={(data) => update.mutate({ id: c.id, data })}
            onDelete={() => {
              if (window.confirm(`Delete category "${c.name}"?`)) {
                remove.mutate(c.id)
              }
            }}
          />
        ))}
        {categories.length === 0 && (
          <p className="px-4 py-4 text-sm text-gray-400">No categories yet.</p>
        )}
      </div>
      <AddCategoryForm isIncome={isIncome} onSuccess={() => {}} />
    </div>
  )
}

export default function Categories() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  })

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold mb-6">Categories</h1>

      {isLoading && <div className="text-gray-500">Loading categories…</div>}
      {error && <div className="text-red-600">Failed to load categories.</div>}

      {data && (
        <div className="space-y-6">
          <CategoryGroup title="Income" categories={data.filter((c) => c.is_income)} />
          <CategoryGroup title="Expense" categories={data.filter((c) => !c.is_income)} />
        </div>
      )}
    </div>
  )
}
