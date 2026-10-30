'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Spinner } from '@/components/ui/spinner'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { useTokenRefresh } from '@/hooks/use-token-refresh'
import { withLoginNext } from '@smartserve/ui'

export function AuthReadyGate({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { ready, authenticated, deviceConfigured } = useAuthReady()
  useTokenRefresh()

  useEffect(() => {
    if (!ready) return
    if (!deviceConfigured) {
      router.replace('/setup')
      return
    }
    if (!authenticated) {
      const next = `${pathname}${window.location.search}`
      router.replace(withLoginNext('/login', next))
    }
  }, [ready, authenticated, deviceConfigured, pathname, router])

  if (!ready || !deviceConfigured || !authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return children
}
