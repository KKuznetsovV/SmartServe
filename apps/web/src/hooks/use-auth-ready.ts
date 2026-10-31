'use client'

import { useEffect, useState } from 'react'
import { useHasHydrated } from '@smartserve/ui'
import { useAuthStore } from '@/lib/auth-store'
import { bootstrapAuthSession } from '@/lib/auth-session'

/**
 * Gate for "auth is ready to decide": persist has rehydrated and the silent
 * cookie refresh has finished, so layout guards stay on the spinner instead of
 * bouncing to /login.
 */
export function useAuthReady() {
  const hydrated = useHasHydrated(useAuthStore)
  const [bootstrapped, setBootstrapped] = useState(false)
  const accessToken = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    if (!hydrated) return
    void bootstrapAuthSession().finally(() => setBootstrapped(true))
  }, [hydrated])

  const ready = hydrated && bootstrapped
  return {
    ready,
    authenticated: ready && Boolean(accessToken),
  }
}
