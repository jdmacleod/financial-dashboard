import { useQuery } from "@tanstack/react-query"
import { useAuth } from "@/hooks/useAuth"
import { membersApi } from "@/api/members"
import { householdApi } from "@/api/household"

function deriveInitials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return displayName.slice(0, 2).toUpperCase() || "?"
}

export function useCurrentUser() {
  const memberId = useAuth((s) => s.memberId)
  const role = useAuth((s) => s.role)

  const memberQuery = useQuery({
    queryKey: ["current-member", memberId],
    queryFn: () => membersApi.get(memberId!),
    enabled: !!memberId,
    staleTime: 5 * 60_000,
  })

  const householdQuery = useQuery({
    queryKey: ["household"],
    queryFn: () => householdApi.get(),
    staleTime: 5 * 60_000,
  })

  const displayName = memberQuery.data?.display_name ?? null
  const roleFallback = role ? role.charAt(0).toUpperCase() + role.slice(1) : "Account"
  const resolvedName = displayName ?? roleFallback
  const firstName = resolvedName.split(" ")[0]
  const initials = displayName ? deriveInitials(displayName) : (role?.[0]?.toUpperCase() ?? "?")
  const householdName = householdQuery.data?.name ?? null

  return {
    displayName: resolvedName,
    firstName,
    initials,
    householdName,
    role,
    isLoading: memberQuery.isLoading || householdQuery.isLoading,
  }
}
