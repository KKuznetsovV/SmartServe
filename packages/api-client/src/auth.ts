import type { PinStaff, TokenPair, User } from '@smartserve/types'

import type { Http } from './client'

export function createAuthResource(http: Http) {
  return {
    login: (email: string, password: string) => http.post<TokenPair>('/auth/login', { email, password }),
    pinLogin: (locationId: string, userId: string, pin: string) =>
      http.post<TokenPair>('/auth/pin', { locationId, userId, pin }),
    pinStaff: (locationId: string) =>
      http.get<PinStaff[]>(`/auth/pin/staff?locationId=${encodeURIComponent(locationId)}`),
    refresh: (refreshToken: string) => http.post<TokenPair>('/auth/refresh', { refreshToken }),
    me: () => http.get<User>('/auth/me'),
  }
}
