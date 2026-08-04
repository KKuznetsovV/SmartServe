import type { Discount } from '@smartserve/types'

import type { Http } from './client'

export function createDiscountsResource(http: Http) {
  return {
    list: (businessId: string) => http.get<Discount[]>(`/businesses/${businessId}/discounts`),
    create: (data: Omit<Discount, 'id' | 'createdAt'>) => http.post<Discount>('/discounts', data),
    update: (
      id: string,
      data: Partial<Pick<Discount, 'name' | 'value' | 'minOrderAmount' | 'active' | 'expiresAt'>>,
    ) => http.patch<Discount>(`/discounts/${id}`, data),
    delete: (id: string) => http.del<void>(`/discounts/${id}`),
  }
}
