import type { DisplayOrder, Order, OrderItem, OrderItemModifierInput } from '@smartserve/types'

import type { Http } from './client'

/** One selected item plus how many of its units a bulk action applies to (omit/undefined = whole item). */
export interface ItemSelection {
  itemId: string
  quantity?: number
}

export function createOrdersResource(http: Http) {
  return {
    list: (locationId: string, status?: string) =>
      http.get<Order[]>(`/locations/${locationId}/orders${status ? `?status=${status}` : ''}`),
    get: (id: string) => http.get<Order>(`/orders/${id}`),
    create: (data: Pick<Order, 'locationId' | 'tableId' | 'channel'> & Partial<Pick<Order, 'guestCount'>>) =>
      http.post<Order>('/orders', data),
    addItem: (
      orderId: string,
      item: Omit<
        OrderItem,
        'id' | 'orderId' | 'status' | 'sortOrder' | 'fireCourse' | 'discountAmount' | 'isComped' | 'modifiers'
      > &
        Partial<Pick<OrderItem, 'fireCourse'>> & { modifiers?: OrderItemModifierInput[] },
    ) => http.post<OrderItem>(`/orders/${orderId}/items`, item),
    updateItemStatus: (orderId: string, itemId: string, status: string) =>
      http.patch<OrderItem>(`/orders/${orderId}/items/${itemId}/status`, { status }),
    updateItem: (
      orderId: string,
      itemId: string,
      data: Partial<Pick<OrderItem, 'qty' | 'notes' | 'fireCourse'>> & {
        modifiers?: OrderItemModifierInput[]
      },
    ) => http.patch<OrderItem>(`/orders/${orderId}/items/${itemId}`, data),
    reorderItems: (orderId: string, ids: string[]) =>
      http.post<void>(`/orders/${orderId}/items/reorder`, { ids }),
    removeItem: (orderId: string, itemId: string) => http.del<void>(`/orders/${orderId}/items/${itemId}`),
    submit: (orderId: string) => http.post<Order>(`/orders/${orderId}/submit`, {}),
    cancel: (orderId: string) => http.post<Order>(`/orders/${orderId}/cancel`, {}),
    applyDiscount: (orderId: string, code: string) => http.post<Order>(`/orders/${orderId}/discount`, { code }),
    assignGuests: (
      orderId: string,
      assignments: (ItemSelection & { guestNumber: number | null })[],
    ) => http.post<Order>(`/orders/${orderId}/items/assign-guests`, { assignments }),
    applyItemDiscount: (
      orderId: string,
      items: ItemSelection[],
      discountType: 'percent' | 'fixed' | null,
      discountValue: number | null,
    ) =>
      http.post<Order>(`/orders/${orderId}/items/discount`, {
        items,
        discountType,
        discountValue,
      }),
    setItemComp: (orderId: string, items: ItemSelection[], comped: boolean) =>
      http.post<Order>(`/orders/${orderId}/items/comp`, { items, comped }),
    deleteItems: (
      orderId: string,
      items: ItemSelection[],
      override?: { managerUserId: string; pin: string; reason: string },
    ) => http.post<Order>(`/orders/${orderId}/items/delete`, { items, override: override ?? null }),
    fireCourse: (orderId: string, course: number) =>
      http.post<Order>(`/orders/${orderId}/fire-course`, { course }),
    publicDisplay: (deviceToken: string) =>
      http.get<DisplayOrder[]>('/public/display/orders', { 'X-Device-Token': deviceToken }),
  }
}

