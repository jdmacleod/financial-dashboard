import { create } from "zustand"

type Theme = "light" | "dark" | "system"

function resolveIsDark(theme: Theme): boolean {
  return (
    theme === "dark" ||
    (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches)
  )
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = resolveIsDark(theme) ? "dark" : "light"
}

function readStoredTheme(): Theme {
  // Migrate from old "theme" key to "hl-theme"
  const legacy = localStorage.getItem("theme") as Theme | null
  const current = localStorage.getItem("hl-theme") as Theme | null
  if (current) return current
  if (legacy) {
    localStorage.setItem("hl-theme", legacy)
    localStorage.removeItem("theme")
    return legacy
  }
  return "system"
}

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
}

export const useTheme = create<ThemeState>((set) => ({
  theme: readStoredTheme(),
  setTheme: (theme) => {
    localStorage.setItem("hl-theme", theme)
    applyTheme(theme)
    set({ theme })
  },
}))

// Apply theme immediately on module load (index.html script covers the pre-React window)
applyTheme(readStoredTheme())

// React to OS theme changes when set to "system"
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  const stored = (localStorage.getItem("hl-theme") as Theme) ?? "system"
  if (stored === "system") applyTheme("system")
})
