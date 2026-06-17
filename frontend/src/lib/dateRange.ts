import { format, subMonths, subYears, startOfMonth, endOfMonth } from "date-fns"

export function toIso(d: Date): string {
  return format(d, "yyyy-MM-dd")
}

export function currentMonthRange(): { from: string; to: string } {
  const now = new Date()
  return { from: toIso(startOfMonth(now)), to: toIso(endOfMonth(now)) }
}

export function lastNMonthsRange(n: number): { from: string; to: string } {
  const now = new Date()
  return { from: toIso(startOfMonth(subMonths(now, n - 1))), to: toIso(endOfMonth(now)) }
}

export function lastNYearsRange(n: number): { from: string; to: string } {
  const now = new Date()
  return { from: toIso(startOfMonth(subYears(now, n))), to: toIso(endOfMonth(now)) }
}

export function currentMonthKey(): string {
  return format(new Date(), "yyyy-MM")
}
