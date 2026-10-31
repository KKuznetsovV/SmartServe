import type { Device, DeviceRegister, DeviceType, PinStaff, TokenPair, User } from '@smartserve/types'

import type { Http } from './client'

export function createAuthResource(http: Http) {
  return {
    login: (email: string, password: string) => http.post<TokenPair>('/auth/login', { email, password }),
    pinLogin: (locationId: string, userId: string, pin: string, deviceToken: string) =>
      http.post<TokenPair>(
        '/auth/pin',
        { locationId, userId, pin },
        { 'X-Device-Token': deviceToken },
      ),
    pinStaff: (locationId: string, deviceToken: string) =>
      http.get<PinStaff[]>(`/auth/pin/staff?locationId=${encodeURIComponent(locationId)}`, {
        'X-Device-Token': deviceToken,
      }),
    listDevices: (locationId: string) => http.get<Device[]>(`/locations/${locationId}/devices`),
    registerDevice: (locationId: string, data: { name: string; type: DeviceType }) =>
      http.post<DeviceRegister>(`/locations/${locationId}/devices`, data),
    revokeDevice: (deviceId: string) => http.post<Device>(`/devices/${deviceId}/revoke`, {}),
    refresh: () => http.post<TokenPair>('/auth/refresh', {}),
    logout: () => http.post<void>('/auth/logout', {}),
    me: () => http.get<User>('/auth/me'),
  }
}
