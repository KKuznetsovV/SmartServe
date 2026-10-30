'use client'

import { useHasHydrated } from '@smartserve/ui'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'

/**
 * Gate for "auth + device are ready to decide".
 *
 * Today that is persist hydration of both stores. S8's silent refresh should
 * plug in here and keep `ready` false until bootstrap finishes.
 */
export function useAuthReady() {
  const authReady = useHasHydrated(useAuthStore)
  const deviceReady = useHasHydrated(useDeviceStore)
  const ready = authReady && deviceReady
  const accessToken = useAuthStore((s) => s.accessToken)
  const locationId = useDeviceStore((s) => s.locationId)
  return {
    ready,
    authenticated: ready && Boolean(accessToken),
    deviceConfigured: ready && Boolean(locationId),
  }
}
