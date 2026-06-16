import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { membersApi } from "@/api/members"
import type { MemberResponse } from "@/api/types"

const ROLE_LABELS: Record<string, string> = {
  primary: "Primary",
  partner: "Partner",
  dependent: "Dependent",
}

const ROLE_COLORS: Record<string, string> = {
  primary: "bg-indigo-100 text-indigo-700",
  partner: "bg-emerald-100 text-emerald-700",
  dependent: "bg-gray-100 text-gray-600",
}

function MemberSlideOver({
  member,
  onClose,
}: {
  member: MemberResponse
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [displayName, setDisplayName] = useState(member.display_name)
  const [error, setError] = useState<string | null>(null)

  const update = useMutation({
    mutationFn: (name: string) => membersApi.update(member.id, { display_name: name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] })
      onClose()
    },
    onError: () => setError("Failed to update member."),
  })

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-sm bg-white shadow-xl p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Edit member</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Display name</label>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div>
          <span className="block text-sm font-medium text-gray-700 mb-1">Role</span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[member.role]}`}>
            {ROLE_LABELS[member.role]}
          </span>
          <p className="mt-1 text-xs text-gray-400">Role changes are not supported in this view.</p>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="flex gap-3 mt-auto">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => update.mutate(displayName)}
            disabled={update.isPending || displayName === member.display_name}
            className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {update.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Members() {
  const { data: members, isLoading, error } = useQuery({
    queryKey: ["members"],
    queryFn: membersApi.list,
  })
  const [selected, setSelected] = useState<MemberResponse | null>(null)

  if (isLoading) return <div className="p-8 text-gray-500">Loading members…</div>
  if (error) return <div className="p-8 text-red-600">Failed to load members.</div>

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Members</h1>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        {members?.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelected(m)}
            className="w-full flex items-center gap-4 px-4 py-3 hover:bg-gray-50 text-left transition-colors"
          >
            <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-sm shrink-0">
              {m.display_name.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 truncate">{m.display_name}</p>
              <p className="text-sm text-gray-500">{m.is_active ? "Active" : "Inactive"}</p>
            </div>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_COLORS[m.role]}`}>
              {ROLE_LABELS[m.role]}
            </span>
          </button>
        ))}
        {members?.length === 0 && (
          <p className="px-4 py-8 text-center text-gray-400">No members yet.</p>
        )}
      </div>

      {selected && <MemberSlideOver member={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
