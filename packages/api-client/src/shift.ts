import type { Shift } from '@smartserve/types'

import type { Http } from './client'

export function createShiftsResource(http: Http) {
  return {
    open: (locationId: string, openingCash: number, notes?: string) =>
      http.post<Shift>(`/locations/${locationId}/shifts/open`, { openingCash, notes }),
    close: (shiftId: string, closingCash: number, notes?: string) =>
      http.post<Shift>(`/shifts/${shiftId}/close`, { closingCash, notes }),
    current: (locationId: string) => http.get<Shift | null>(`/locations/${locationId}/shifts/current`),
    list: (locationId: string) => http.get<Shift[]>(`/locations/${locationId}/shifts`),
  }
}
