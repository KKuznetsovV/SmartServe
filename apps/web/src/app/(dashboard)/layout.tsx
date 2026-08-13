'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/layout/sidebar'
import { useAuthStore } from '@/lib/auth-store'
import { useTokenRefresh } from '@/hooks/use-token-refresh'
import { useLocationWs } from '@/hooks/use-ws'
import { Spinner } from '@/components/ui/spinner'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const accessToken = useAuthStore((s) => s.accessToken)
  const locationId = useAuthStore((s) => s.activeLocationId)
  useTokenRefresh()
  // Connected here (not per-page) so real-time events — e.g. an AI-driven price change —
  // reach whichever dashboard screen a manager currently has open, not just Dashboard.
  useLocationWs(locationId)

  useEffect(() => {
    if (!accessToken) {
      router.replace('/login')
    }
  }, [accessToken, router])

  if (!accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  )
}
