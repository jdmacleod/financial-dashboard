import { useQuery } from "@tanstack/react-query"
import { reportsApi } from "@/api/reports"
import type { MemberMilestones, MilestoneItem } from "@/api/types"

function MilestoneRow({ m, isNext }: { m: MilestoneItem; isNext: boolean }) {
  return (
    <li className="flex gap-3">
      <div className="flex flex-col items-center">
        <span
          className={`mt-1 h-3 w-3 shrink-0 rounded-full border-2 ${
            m.reached
              ? "border-emerald-500 bg-emerald-500"
              : isNext
                ? "border-indigo-500 bg-white"
                : "border-gray-300 bg-white"
          }`}
        />
        <span className="w-px flex-1 bg-gray-200" />
      </div>
      <div className={`pb-5 ${m.reached ? "opacity-60" : ""}`}>
        <p className="text-sm font-medium text-gray-900">
          {m.label}
          {isNext && (
            <span className="ml-2 rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
              Next
            </span>
          )}
        </p>
        <p className="text-xs text-gray-500">
          {m.year} · age {m.age_label}
          {m.reached && " · reached"}
        </p>
      </div>
    </li>
  )
}

function MemberTimeline({ m }: { m: MemberMilestones }) {
  const nextIdx = m.milestones.findIndex((x) => !x.reached)
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="mb-4">
        <p className="font-semibold text-gray-900">{m.display_name}</p>
        <p className="text-xs text-gray-500">
          {m.current_age !== null ? `Age ${m.current_age}` : "Date of birth not set"}
        </p>
      </div>
      {m.milestones.length > 0 ? (
        <ul>
          {m.milestones.map((item, i) => (
            <MilestoneRow key={item.key} m={item} isNext={i === nextIdx} />
          ))}
        </ul>
      ) : (
        <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-600">
          {m.note ?? "No milestones to show."}
        </p>
      )}
    </div>
  )
}

export default function ReportMilestones() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["reports", "age-milestones"],
    queryFn: () => reportsApi.ageMilestones(),
  })

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Retirement Milestones</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          The age-based events ahead for each household member: penalty-free withdrawals (59½),
          Social Security (earliest and full retirement age), Medicare (65), and required minimum
          distributions. Set a member's date of birth to populate their timeline.
        </p>
      </div>

      {isLoading && <div className="text-sm text-gray-400 py-8 text-center">Loading…</div>}
      {error && <div className="text-sm text-red-500 py-4">Failed to load milestones.</div>}

      {data && data.members.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <p className="text-sm text-gray-500">No household members yet.</p>
        </div>
      )}

      {data && data.members.length > 0 && (
        <div className="space-y-4">
          {data.members.map((m) => (
            <MemberTimeline key={m.member_id} m={m} />
          ))}
        </div>
      )}
    </div>
  )
}
