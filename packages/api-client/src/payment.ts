import type { Payment } from '@smartserve/types'

import type { Http } from './client'

export function createPaymentsResource(http: Http) {
  return {
    create: (
      data: Pick<Payment, 'orderId' | 'method' | 'amount'> & Partial<Pick<Payment, 'tipAmount' | 'guestNumber'>>,
    ) => http.post<Payment>('/payments', data),
    get: (id: string) => http.get<Payment>(`/payments/${id}`),
    listByOrder: (orderId: string) => http.get<Payment[]>(`/orders/${orderId}/payments`),
  }
}
