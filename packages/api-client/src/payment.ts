import type { Payment } from '@smartserve/types'

import type { Http } from './client'

export function createPaymentsResource(http: Http) {
  return {
    create: (
      data: Pick<Payment, 'orderId' | 'method' | 'amount'> & Partial<Pick<Payment, 'tipAmount' | 'guestNumber'>>,
      extraHeaders?: Record<string, string>,
    ) => http.post<Payment>('/payments', data, extraHeaders),
    refund: (
      id: string,
      data: { managerUserId: string; pin: string; reason: string },
    ) => http.post<Payment>(`/payments/${id}/refund`, data),
    get: (id: string) => http.get<Payment>(`/payments/${id}`),
    listByOrder: (orderId: string) => http.get<Payment[]>(`/orders/${orderId}/payments`),
  }
}
