interface DataRowProps {
  label: React.ReactNode
  children: React.ReactNode
  className?: string
}

export function DataRow({ label, children, className }: DataRowProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "8px 16px",
        borderBottom: "1px solid var(--bd)",
      }}
      className={className}
    >
      <span style={{ flex: 1, fontSize: "13px", color: "var(--text3)" }}>{label}</span>
      <span style={{ fontSize: "13px", color: "var(--text)" }}>{children}</span>
    </div>
  )
}
