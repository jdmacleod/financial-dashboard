import { useTheme } from "@/stores/themeStore"

type Theme = "light" | "dark" | "system"

const OPTIONS: { value: Theme; label: string; description: string }[] = [
  { value: "light", label: "Light", description: "Always use the light theme" },
  { value: "dark", label: "Dark", description: "Always use the dark theme" },
  {
    value: "system",
    label: "System",
    description: "Follow your operating system preference",
  },
]

export default function SettingsAppearance() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Appearance</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Choose how HearthLedger looks on this device.
        </p>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
        {OPTIONS.map(({ value, label, description }) => (
          <label
            key={value}
            className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750"
          >
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{label}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
            </div>
            <input
              type="radio"
              name="theme"
              value={value}
              checked={theme === value}
              onChange={() => setTheme(value)}
              className="h-4 w-4 accent-indigo-600"
            />
          </label>
        ))}
      </div>
    </div>
  )
}
