import type { User } from '@smartserve/types'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'

let bootstrapPromise: Promise<void> | null = null

export async function syncLocationFromDevice(user: User): Promise<void> {
  const deviceToken = useDeviceStore.getState().deviceToken
  if (!deviceToken || !user.businessId) return
  const device = await apiClient.auth.currentDevice(deviceToken)
  useAuthStore.getState().setActiveLocation(user.businessId, device.locationId)
  const stored = useDeviceStore.getState()
  if (stored.locationId !== device.locationId && stored.deviceType && stored.deviceName) {
    useDeviceStore.getState().setDevice({
      locationId: device.locationId,
      deviceToken,
      deviceType: stored.deviceType,
      deviceName: stored.deviceName,
    })
  }
}

export function bootstrapAuthSession(): Promise<void> {
  if (!bootstrapPromise) {
    bootstrapPromise = (async () => {
      try {
        if (!useAuthStore.getState().accessToken) {
          const tokens = await apiClient.auth.refresh()
          useAuthStore.getState().setTokens(tokens.accessToken)
        }
        if (!useAuthStore.getState().accessToken) return
        const user = await apiClient.auth.me()
        useAuthStore.getState().setAuth(useAuthStore.getState().accessToken as string, user)
        await syncLocationFromDevice(user)
      } catch {
        if (!useAuthStore.getState().accessToken) {
          useAuthStore.getState().clearAuth()
        }
      }
    })()
  }
  return bootstrapPromise
}

export async function signOut(): Promise<void> {
  try {
    await apiClient.auth.logout()
  } catch {
    // Cookie may already be gone.
  }
  useAuthStore.getState().clearAuth()
  bootstrapPromise = null
}
