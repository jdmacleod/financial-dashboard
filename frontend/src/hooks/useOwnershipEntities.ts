import { useQuery } from "@tanstack/react-query"
import { ownershipEntitiesApi } from "@/api/ownershipEntities"
import type { OwnershipEntityResponse } from "@/api/types"

/**
 * Shared query for the household's ownership entities (trusts, LLCs, custodial
 * accounts). Cached under a stable key so multiple callers — account rows,
 * detail panels, property cards — share a single request.
 */
export function useOwnershipEntities() {
  return useQuery({
    queryKey: ["ownership-entities"],
    queryFn: () => ownershipEntitiesApi.list(),
    staleTime: 60_000,
  })
}

/** Resolve the ownership entity an account/asset is titled to, or null. */
export function useOwnershipEntity(entityId: string | null): OwnershipEntityResponse | null {
  const { data } = useOwnershipEntities()
  if (!entityId || !data) return null
  return data.find((e) => e.id === entityId) ?? null
}
