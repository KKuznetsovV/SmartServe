import type { Table } from '@smartserve/types'

import type { Http } from './client'

export function createTablesResource(http: Http) {
  return {
    list: (locationId: string, include?: 'status') =>
      http.get<Table[]>(`/locations/${locationId}/tables${include ? `?include=${include}` : ''}`),
    create: (data: Omit<Table, 'id'>) => http.post<Table>('/tables', data),
    update: (id: string, data: Partial<Table>) => http.patch<Table>(`/tables/${id}`, data),
    delete: (id: string) => http.del<void>(`/tables/${id}`),
  }
}
