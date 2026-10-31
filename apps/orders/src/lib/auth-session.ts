import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'

let bootstrapPromise: Promise<void> | null = null

export function bootstrapAuthSession(): Promise<void> {
  if (!bootstrapPromise) {
    bootstrapPromise = (async () => {
      if (useAuthStore.getState().accessToken) return
      try {
        const tokens = await apiClient.auth.refresh()
        useAuthStore.getState().setTokens(tokens.accessToken)
        const user = await apiClient.auth.me()
        useAuthStore.getState().setAuth(tokens.accessToken, user)
      } catch {
        useAuthStore.getState().clearAuth()
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
