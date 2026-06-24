interface DataCardProps {
  children: React.ReactNode
  className?: string
}

export function DataCard({ children, className }: DataCardProps) {
  return (
    <div
      style={{
        background: "var(--card)",
        border: "1px solid var(--bd)",
        borderRadius: "14px",
        overflow: "hidden",
      }}
      className={className}
    >
      {children}
    </div>
  )
}
