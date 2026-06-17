export function formatCurrency(value: string | number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    Number(value),
  )
}

// Append a fixed midday time so `new Date()` parses the date-only string in
// local time instead of UTC, which would otherwise roll back a day in any
// timezone west of UTC.
export function formatDate(value: string): string {
  return new Date(`${value}T12:00:00`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}
