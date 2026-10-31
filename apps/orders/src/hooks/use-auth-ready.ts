'use client'

import { useEffect, useState } from 'react'
import { useHasHydrated } from '@smartserve/ui'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'
import { bootstrapAuthSession } from '@/lib/auth-session'

/**
 * Gate for "auth + device are ready to decide": persist hydration of both
 * stores plus the silent cookie refresh.
 */
export function useAuthReady() {
  const authHydrated = useHasHydrated(useAuthStore)
  const deviceHydrated = useHasHydrated(useDeviceStore)
  const [bootstrapped, setBootstrapped] = useState(false)
  const accessToken = useAuthStore((s) => s.accessToken)
  const locationId = useDeviceStore((s) => s.locationId)
  const deviceToken = useDeviceStore((s) => s.deviceToken)

  useEffect(() => {
    if (!authHydrated || !deviceHydrated) return
    void bootstrapAuthSession().finally(() => setBootstrapped(true))
  }, [authHydrated, deviceHydrated])

  const ready = authHydrated && deviceHydrated && bootstrapped
  return {
    ready,
    authenticated: ready && Boolean(accessToken),
    deviceConfigured: ready && Boolean(locationId && deviceToken),
  }
}
