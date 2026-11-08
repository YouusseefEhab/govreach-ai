// Stylized government-building emblem (pediment + columns + base).
export default function Emblem({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path d="M12 2l9 5v2H3V7l9-5z" fill="currentColor" />
      <rect x="4" y="10" width="2.4" height="8" fill="currentColor" />
      <rect x="10.8" y="10" width="2.4" height="8" fill="currentColor" />
      <rect x="17.6" y="10" width="2.4" height="8" fill="currentColor" />
      <rect x="3" y="19" width="18" height="2.4" rx="0.6" fill="currentColor" />
    </svg>
  )
}
