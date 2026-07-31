import { createApiClient } from '@smartserve/api-client'
import { useAuthStore } from '@/lib/auth-store'

const BASE_URL =
  (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/api/v1'

export const apiClient = createApiClient({
  baseUrl: BASE_URL,
  getAccessToken: () => useAuthStore.getState().accessToken,
  onUnauthorized: () => useAuthStore.getState().clearAuth(),
})
