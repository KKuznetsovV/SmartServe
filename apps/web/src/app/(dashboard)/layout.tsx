'use client'

import { Sidebar } from '@/components/layout/sidebar'
import { AuthReadyGate } from '@/components/auth-ready-gate'
import { useAuthStore } from '@/lib/auth-store'
import { useTokenRefresh } from '@/hooks/use-token-refresh'
import { useLocationWs } from '@/hooks/use-ws'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const locationId = useAuthStore((s) => s.activeLocationId)
  useTokenRefresh()
  // Connected here (not per-page) so real-time events — e.g. an AI-driven price change —
  // reach whichever dashboard screen a manager currently has open, not just Dashboard.
  useLocationWs(locationId)

  return (
    <AuthReadyGate>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </AuthReadyGate>
  )
}
