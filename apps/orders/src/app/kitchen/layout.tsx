import type { ReactNode } from 'react'
import { AuthReadyGate } from '@/components/auth-ready-gate'

// Full-screen dark layout for kitchen display — no sidebar
export default function KitchenLayout({ children }: { children: ReactNode }) {
  return (
    <AuthReadyGate>
      <div className="bg-zinc-950 text-zinc-100 min-h-screen">{children}</div>
    </AuthReadyGate>
  )
}
