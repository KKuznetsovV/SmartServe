import { createApiClient } from '@smartserve/api-client'
import { useAuthStore } from '@/lib/auth-store'

const BASE_URL =
  (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080') + '/api/v1'

export const apiClient = createApiClient({
  baseUrl: BASE_URL,
  getAccessToken: () => useAuthStore.getState().accessToken,
  getRefreshToken: () => useAuthStore.getState().refreshToken,
  onTokensRefreshed: (accessToken, refreshToken) =>
    useAuthStore.getState().setTokens(accessToken, refreshToken),
  onUnauthorized: () => useAuthStore.getState().clearAuth(),
})
