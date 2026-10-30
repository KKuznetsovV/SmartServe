'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Spinner } from '@/components/ui/spinner'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { withLoginNext } from '@smartserve/ui'

export function AuthReadyGate({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { ready, authenticated } = useAuthReady()

  useEffect(() => {
    if (!ready || authenticated) return
    const next = `${pathname}${window.location.search}`
    router.replace(withLoginNext('/login', next))
  }, [ready, authenticated, pathname, router])

  if (!ready || !authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return children
}
