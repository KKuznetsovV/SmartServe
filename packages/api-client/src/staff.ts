import type { User } from '@smartserve/types'

import type { Http } from './client'

export function createStaffResource(http: Http) {
  return {
    list: (businessId: string) => http.get<User[]>(`/businesses/${businessId}/staff`),
    create: (data: Omit<User, 'id'> & { password?: string; pin?: string }) => http.post<User>('/staff', data),
    update: (id: string, data: Partial<User>) => http.patch<User>(`/staff/${id}`, data),
  }
}
