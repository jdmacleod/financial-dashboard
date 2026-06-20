import { type UseQueryResult } from "@tanstack/react-query"
import { Skeleton } from "@/components/ui/skeleton"

interface QueryGuardProps<T> {
  query: UseQueryResult<T>
  empty?: React.ReactNode
  children: (data: T) => React.ReactNode
}

export function QueryGuard<T>({ query, empty, children }: QueryGuardProps<T>) {
  if (query.isPending) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-8 w-5/6" />
      </div>
    )
  }

  if (query.isError) {
    return (
      <div
        className="flex items-center justify-center p-8 text-sm"
        style={{ color: "var(--liab)" }}
      >
        Failed to load data. Try refreshing.
      </div>
    )
  }

  const data = query.data
  if (data === undefined || (Array.isArray(data) && data.length === 0)) {
    return empty ?? null
  }

  return <>{children(data)}</>
}
