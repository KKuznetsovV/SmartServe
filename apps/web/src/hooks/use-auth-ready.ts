'use client'

import { useHasHydrated } from '@smartserve/ui'
import { useAuthStore } from '@/lib/auth-store'

/**
 * Gate for "auth is ready to decide".
 *
 * Today that means Zustand persist has rehydrated from localStorage. S8 will
 * also run a silent refresh on load and should keep `ready` false until that
 * bootstrap finishes, so layout guards stay on the spinner instead of
 * bouncing to /login.
 */
export function useAuthReady() {
  const ready = useHasHydrated(useAuthStore)
  const accessToken = useAuthStore((s) => s.accessToken)
  return {
    ready,
    authenticated: ready && Boolean(accessToken),
  }
}
