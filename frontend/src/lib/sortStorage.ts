// Persist a chosen sort key to localStorage so power users don't re-apply it
// every visit. Stored values are validated against the allowed set on read, so a
// renamed/removed sort option falls back to the default rather than sticking.
// Shared across the Budgets, Accounts, and (future) Investments/Real Estate
// listings so they behave identically.

export function loadSort<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const stored = localStorage.getItem(key)
    if (stored && (allowed as readonly string[]).includes(stored)) return stored as T
  } catch {
    // localStorage unavailable (private mode / SSR) — use the default.
  }
  return fallback
}

export function persistSort(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Persistence is a progressive enhancement; ignore write failures.
  }
}
