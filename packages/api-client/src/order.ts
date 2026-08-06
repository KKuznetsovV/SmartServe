import type { Order, OrderItem } from '@smartserve/types'

import type { Http } from './client'

export function createOrdersResource(http: Http) {
  return {
    list: (locationId: string, status?: string) =>
      http.get<Order[]>(`/locations/${locationId}/orders${status ? `?status=${status}` : ''}`),
    get: (id: string) => http.get<Order>(`/orders/${id}`),
    create: (data: Pick<Order, 'locationId' | 'tableId' | 'channel'>) => http.post<Order>('/orders', data),
    addItem: (orderId: string, item: Omit<OrderItem, 'id' | 'orderId' | 'status' | 'sortOrder'>) =>
      http.post<OrderItem>(`/orders/${orderId}/items`, item),
    updateItemStatus: (orderId: string, itemId: string, status: string) =>
      http.patch<OrderItem>(`/orders/${orderId}/items/${itemId}/status`, { status }),
    updateItem: (
      orderId: string,
      itemId: string,
      data: Partial<Pick<OrderItem, 'qty' | 'notes' | 'modifiers'>>,
    ) => http.patch<OrderItem>(`/orders/${orderId}/items/${itemId}`, data),
    reorderItems: (orderId: string, ids: string[]) =>
      http.post<void>(`/orders/${orderId}/items/reorder`, { ids }),
    removeItem: (orderId: string, itemId: string) => http.del<void>(`/orders/${orderId}/items/${itemId}`),
    submit: (orderId: string) => http.post<Order>(`/orders/${orderId}/submit`, {}),
    cancel: (orderId: string) => http.post<Order>(`/orders/${orderId}/cancel`, {}),
    applyDiscount: (orderId: string, code: string) => http.post<Order>(`/orders/${orderId}/discount`, { code }),
    publicActive: (locationId: string) => http.get<Order[]>(`/public/locations/${locationId}/orders`),
  }
}
