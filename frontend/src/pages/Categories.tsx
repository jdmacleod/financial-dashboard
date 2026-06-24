import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { categoriesApi } from "@/api/categories"
import { ApiError } from "@/api/client"
import type { CategoryResponse } from "@/api/types"

// ── Color dot — clickable to open native color picker ─────────────────────────

function ColorDot({
  color,
  onChange,
  disabled,
}: {
  color: string
  onChange: (hex: string) => void
  disabled?: boolean
}) {
  return (
    <label
      style={{
        position: "relative",
        display: "inline-block",
        cursor: disabled ? "default" : "pointer",
      }}
      title={disabled ? undefined : "Change color"}
    >
      <span
        style={{
          display: "inline-block",
          width: "12px",
          height: "12px",
          borderRadius: "50%",
          background: color,
          border: "1px solid rgba(0,0,0,0.15)",
          flexShrink: 0,
        }}
      />
      {!disabled && (
        <input
          type="color"
          value={color}
          onChange={(e) => onChange(e.target.value)}
          style={{
            position: "absolute",
            opacity: 0,
            width: "1px",
            height: "1px",
            top: 0,
            left: 0,
            pointerEvents: "none",
          }}
          tabIndex={-1}
        />
      )}
    </label>
  )
}

// ── Individual category row ───────────────────────────────────────────────────

function CategoryRow({
  category,
  onUpdate,
  onDelete,
}: {
  category: CategoryResponse
  onUpdate: (data: { name?: string; color_hex?: string }) => void
  onDelete: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(category.name)

  if (editing) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 16px",
          borderBottom: "1px solid var(--bd)",
        }}
      >
        <ColorDot color={category.color_hex} onChange={(hex) => onUpdate({ color_hex: hex })} />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          style={{
            flex: 1,
            background: "var(--input-bg, var(--card))",
            border: "1px solid var(--accent)",
            borderRadius: "6px",
            padding: "3px 8px",
            fontSize: "13px",
            color: "var(--text)",
            outline: "none",
          }}
        />
        <button
          onClick={() => {
            onUpdate({ name })
            setEditing(false)
          }}
          style={{
            fontSize: "12px",
            color: "var(--accent)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "2px 4px",
          }}
        >
          Save
        </button>
        <button
          onClick={() => {
            setName(category.name)
            setEditing(false)
          }}
          style={{
            fontSize: "12px",
            color: "var(--muted)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: "2px 4px",
          }}
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "6px 16px",
        borderBottom: "1px solid var(--bd)",
      }}
    >
      <ColorDot color={category.color_hex} onChange={(hex) => onUpdate({ color_hex: hex })} />
      <span style={{ flex: 1, fontSize: "13px", color: "var(--text)" }}>{category.name}</span>
      {category.is_system && (
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.05em",
            color: "var(--faint)",
            background: "var(--bd)",
            borderRadius: "4px",
            padding: "1px 5px",
          }}
        >
          SYSTEM
        </span>
      )}
      {!category.is_system && (
        <>
          <button
            onClick={() => setEditing(true)}
            style={{
              fontSize: "12px",
              color: "var(--muted)",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "2px 4px",
            }}
          >
            Rename
          </button>
          <button
            onClick={onDelete}
            style={{
              fontSize: "12px",
              color: "var(--liab)",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "2px 4px",
            }}
          >
            Delete
          </button>
        </>
      )}
    </div>
  )
}

// ── Parent group with collapsible children ────────────────────────────────────

function ParentGroup({
  parent,
  children,
  onUpdate,
  onDelete,
}: {
  parent: CategoryResponse
  children: CategoryResponse[]
  onUpdate: (id: string, data: { name?: string; color_hex?: string }) => void
  onDelete: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div>
      {/* Parent row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "8px 16px",
          borderBottom: "1px solid var(--bd)",
          background: "var(--row-alt, rgba(255,255,255,0.02))",
        }}
      >
        <button
          onClick={() => setExpanded((p) => !p)}
          aria-label={expanded ? "Collapse" : "Expand"}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--faint)",
            fontSize: "10px",
            width: "14px",
            padding: 0,
            flexShrink: 0,
          }}
        >
          {expanded ? "▾" : "▸"}
        </button>
        <ColorDot
          color={parent.color_hex}
          onChange={(hex) => onUpdate(parent.id, { color_hex: hex })}
        />
        <span style={{ flex: 1, fontSize: "13px", fontWeight: 600, color: "var(--text)" }}>
          {parent.name}
        </span>
        {parent.is_system && (
          <span
            style={{
              fontSize: "10px",
              fontWeight: 600,
              letterSpacing: "0.05em",
              color: "var(--faint)",
              background: "var(--bd)",
              borderRadius: "4px",
              padding: "1px 5px",
            }}
          >
            SYSTEM
          </span>
        )}
        {!parent.is_system && (
          <>
            <button
              onClick={() => onDelete(parent.id)}
              style={{
                fontSize: "12px",
                color: "var(--liab)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "2px 4px",
              }}
            >
              Delete
            </button>
          </>
        )}
      </div>
      {/* Children */}
      {expanded &&
        children.map((child) => (
          <div key={child.id} style={{ paddingLeft: "24px" }}>
            <CategoryRow
              category={child}
              onUpdate={(data) => onUpdate(child.id, data)}
              onDelete={() => onDelete(child.id)}
            />
          </div>
        ))}
    </div>
  )
}

// ── Add category form ─────────────────────────────────────────────────────────

function AddCategoryForm({
  isIncome,
  parents,
}: {
  isIncome: boolean
  parents: CategoryResponse[]
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [color, setColor] = useState("#888888")
  const [parentId, setParentId] = useState("")
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () =>
      categoriesApi.create({
        name,
        color_hex: color,
        is_income: isIncome,
        parent_category_id: parentId || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] })
      setName("")
      setColor("#888888")
      setParentId("")
      setError(null)
    },
    onError: (err) => {
      setError(err instanceof ApiError ? String(err.detail) : "Failed to create category.")
    },
  })

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 16px",
        borderTop: "1px solid var(--bd)",
        background: "var(--row-alt, rgba(255,255,255,0.02))",
        flexWrap: "wrap",
      }}
    >
      <label style={{ cursor: "pointer" }}>
        <span
          style={{
            display: "inline-block",
            width: "14px",
            height: "14px",
            borderRadius: "50%",
            background: color,
            border: "1px solid rgba(0,0,0,0.15)",
            verticalAlign: "middle",
          }}
        />
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          style={{ width: 0, height: 0, opacity: 0, position: "absolute" }}
        />
      </label>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="New category name"
        style={{
          flex: 1,
          minWidth: "120px",
          background: "var(--input-bg, var(--card))",
          border: "1px solid var(--bd)",
          borderRadius: "6px",
          padding: "4px 8px",
          fontSize: "13px",
          color: "var(--text)",
          outline: "none",
        }}
      />
      <select
        value={parentId}
        onChange={(e) => setParentId(e.target.value)}
        style={{
          background: "var(--input-bg, var(--card))",
          border: "1px solid var(--bd)",
          borderRadius: "6px",
          padding: "4px 8px",
          fontSize: "12px",
          color: "var(--muted)",
          outline: "none",
        }}
      >
        <option value="">No parent</option>
        {parents.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
      <button
        onClick={() => {
          if (!name.trim()) return
          create.mutate()
        }}
        disabled={create.isPending || !name.trim()}
        style={{
          padding: "4px 12px",
          borderRadius: "6px",
          fontSize: "12px",
          fontWeight: 600,
          background: "var(--accent)",
          color: "#fff",
          border: "none",
          cursor: "pointer",
          opacity: create.isPending || !name.trim() ? 0.5 : 1,
        }}
      >
        Add
      </button>
      {error && (
        <span style={{ fontSize: "12px", color: "var(--liab)", width: "100%" }}>{error}</span>
      )}
    </div>
  )
}

// ── Section (Income / Expense) ────────────────────────────────────────────────

function CategorySection({ title, categories }: { title: string; categories: CategoryResponse[] }) {
  const queryClient = useQueryClient()
  const isIncome = title === "Income"

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; color_hex?: string } }) =>
      categoriesApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  })

  const remove = useMutation({
    mutationFn: (id: string) => categoriesApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  })

  const handleDelete = (id: string) => {
    const cat = categories.find((c) => c.id === id)
    if (cat && window.confirm(`Delete category "${cat.name}"?`)) {
      remove.mutate(id)
    }
  }

  const childrenByParent = categories.reduce<Record<string, CategoryResponse[]>>((acc, c) => {
    if (c.parent_category_id) {
      const key = String(c.parent_category_id)
      ;(acc[key] ??= []).push(c)
    }
    return acc
  }, {})

  const parents = categories.filter((c) => !c.parent_category_id)

  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--bd)",
        borderRadius: "14px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--bd)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--faint)",
          }}
        >
          {title}
        </span>
      </div>
      {parents.map((parent) => (
        <ParentGroup
          key={parent.id}
          parent={parent}
          children={childrenByParent[String(parent.id)] ?? []}
          onUpdate={(id, data) => update.mutate({ id, data })}
          onDelete={handleDelete}
        />
      ))}
      {parents.length === 0 && (
        <div
          style={{
            padding: "16px",
            fontSize: "13px",
            color: "var(--faint)",
            textAlign: "center",
          }}
        >
          No categories yet.
        </div>
      )}
      <AddCategoryForm isIncome={isIncome} parents={parents.filter((p) => !p.is_system)} />
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Categories() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["categories"],
    queryFn: categoriesApi.list,
  })

  return (
    <div style={{ maxWidth: "720px", margin: "0 auto" }}>
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "var(--text)", margin: 0 }}>
          Categories
        </h1>
      </div>

      {isLoading && (
        <div style={{ padding: "48px 0", textAlign: "center", color: "var(--muted)" }}>
          Loading categories…
        </div>
      )}
      {error && (
        <div style={{ padding: "24px 0", color: "var(--liab)" }}>Failed to load categories.</div>
      )}

      {data && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <CategorySection title="Income" categories={data.filter((c) => c.is_income)} />
          <CategorySection title="Expense" categories={data.filter((c) => !c.is_income)} />
        </div>
      )}
    </div>
  )
}
