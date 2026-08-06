'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { TopNav } from '@/components/layout/top-nav'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'
import { useTokenRefresh } from '@/hooks/use-token-refresh'
import { Spinner } from '@/components/ui/spinner'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const accessToken = useAuthStore((s) => s.accessToken)
  const locationId = useDeviceStore((s) => s.locationId)
  useTokenRefresh()

  useEffect(() => {
    if (!locationId) {
      router.replace('/setup')
    } else if (!accessToken) {
      router.replace('/login')
    }
  }, [accessToken, locationId, router])

  if (!locationId || !accessToken) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopNav />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  )
}
