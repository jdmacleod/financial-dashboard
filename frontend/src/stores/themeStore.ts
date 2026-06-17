import { create } from "zustand"

type Theme = "light" | "dark" | "system"

function applyTheme(theme: Theme) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches
  const isDark = theme === "dark" || (theme === "system" && prefersDark)
  document.documentElement.classList.toggle("dark", isDark)
}

interface ThemeState {
  theme: Theme
  setTheme: (theme: Theme) => void
}

export const useTheme = create<ThemeState>((set) => ({
  theme: (localStorage.getItem("theme") as Theme) ?? "system",
  setTheme: (theme) => {
    localStorage.setItem("theme", theme)
    applyTheme(theme)
    set({ theme })
  },
}))

// Apply theme immediately on module load
applyTheme((localStorage.getItem("theme") as Theme) ?? "system")

// React to OS theme changes when set to "system"
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  const theme = (localStorage.getItem("theme") as Theme) ?? "system"
  if (theme === "system") applyTheme("system")
})
