import type { ReactNode } from 'react'

// Full-screen dark layout for kitchen display — no sidebar
export default function KitchenLayout({ children }: { children: ReactNode }) {
  return <div className="bg-zinc-950 text-zinc-100 min-h-screen">{children}</div>
}
