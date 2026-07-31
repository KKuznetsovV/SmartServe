import type {
  Business,
  Location,
  MenuCategory,
  MenuItem,
  ModifierGroup,
  Table,
  Order,
  OrderItem,
  Payment,
  Printer,
  User,
  TokenPair,
  AiCommandRequest,
  AiCommandResponse,
  ApiError,
  ReportSummary,
} from '@smartserve/types'

// ─── Config ──────────────────────────────────────────────────────────────────

export interface ApiClientConfig {
  baseUrl: string
  getAccessToken: () => string | null
  onUnauthorized?: () => void
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

async function request<T>(
  config: ApiClientConfig,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = config.getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${config.baseUrl}${path}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    config.onUnauthorized?.()
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const err: ApiError = await response.json()
    throw new Error(err.error?.message ?? `HTTP ${response.status}`)
  }

  // 204 No Content
  if (response.status === 204) return undefined as T

  const json = await response.json()
  return (json.data ?? json) as T
}

// ─── SmartServe API Client ────────────────────────────────────────────────────

export function createApiClient(config: ApiClientConfig) {
  const get = <T>(path: string) => request<T>(config, path)
  const post = <T>(path: string, body: unknown) =>
    request<T>(config, path, { method: 'POST', body: JSON.stringify(body) })
  const put = <T>(path: string, body: unknown) =>
    request<T>(config, path, { method: 'PUT', body: JSON.stringify(body) })
  const patch = <T>(path: string, body: unknown) =>
    request<T>(config, path, { method: 'PATCH', body: JSON.stringify(body) })
  const del = <T>(path: string) => request<T>(config, path, { method: 'DELETE' })

  return {
    // Auth
    auth: {
      login: (email: string, password: string) =>
        post<TokenPair>('/auth/login', { email, password }),
      pinLogin: (locationId: string, pin: string) =>
        post<TokenPair>('/auth/pin', { locationId, pin }),
      refresh: (refreshToken: string) => post<TokenPair>('/auth/refresh', { refreshToken }),
      me: () => get<User>('/auth/me'),
    },

    // Businesses
    businesses: {
      get: (id: string) => get<Business>(`/businesses/${id}`),
      update: (id: string, data: Partial<Business>) => patch<Business>(`/businesses/${id}`, data),
    },

    // Locations
    locations: {
      list: (businessId: string) => get<Location[]>(`/businesses/${businessId}/locations`),
      get: (id: string) => get<Location>(`/locations/${id}`),
      create: (data: Omit<Location, 'id'>) => post<Location>('/locations', data),
      update: (id: string, data: Partial<Location>) => patch<Location>(`/locations/${id}`, data),
    },

    // Menu Categories
    menuCategories: {
      list: (locationId: string) => get<MenuCategory[]>(`/locations/${locationId}/menu/categories`),
      create: (data: Omit<MenuCategory, 'id'>) => post<MenuCategory>('/menu/categories', data),
      update: (id: string, data: Partial<MenuCategory>) =>
        patch<MenuCategory>(`/menu/categories/${id}`, data),
      delete: (id: string) => del<void>(`/menu/categories/${id}`),
      reorder: (locationId: string, ids: string[]) =>
        post<void>(`/locations/${locationId}/menu/categories/reorder`, { ids }),
    },

    // Menu Items
    menuItems: {
      list: (categoryId: string) => get<MenuItem[]>(`/menu/categories/${categoryId}/items`),
      get: (id: string) => get<MenuItem>(`/menu/items/${id}`),
      create: (data: Omit<MenuItem, 'id' | 'modifierGroups'>) =>
        post<MenuItem>('/menu/items', data),
      update: (id: string, data: Partial<MenuItem>) => patch<MenuItem>(`/menu/items/${id}`, data),
      delete: (id: string) => del<void>(`/menu/items/${id}`),
      toggle: (id: string, inStock: boolean) =>
        patch<MenuItem>(`/menu/items/${id}/stock`, { inStock }),
    },

    // Modifier Groups
    modifierGroups: {
      create: (data: Omit<ModifierGroup, 'id'>) =>
        post<ModifierGroup>('/menu/modifier-groups', data),
      update: (id: string, data: Partial<ModifierGroup>) =>
        patch<ModifierGroup>(`/menu/modifier-groups/${id}`, data),
      delete: (id: string) => del<void>(`/menu/modifier-groups/${id}`),
    },

    // Tables
    tables: {
      list: (locationId: string) => get<Table[]>(`/locations/${locationId}/tables`),
      create: (data: Omit<Table, 'id'>) => post<Table>('/tables', data),
      update: (id: string, data: Partial<Table>) => patch<Table>(`/tables/${id}`, data),
      delete: (id: string) => del<void>(`/tables/${id}`),
    },

    // Orders
    orders: {
      list: (locationId: string, status?: string) =>
        get<Order[]>(`/locations/${locationId}/orders${status ? `?status=${status}` : ''}`),
      get: (id: string) => get<Order>(`/orders/${id}`),
      create: (data: Pick<Order, 'locationId' | 'tableId' | 'channel'>) =>
        post<Order>('/orders', data),
      addItem: (orderId: string, item: Omit<OrderItem, 'id' | 'orderId' | 'status'>) =>
        post<OrderItem>(`/orders/${orderId}/items`, item),
      updateItemStatus: (orderId: string, itemId: string, status: string) =>
        patch<OrderItem>(`/orders/${orderId}/items/${itemId}/status`, { status }),
      submit: (orderId: string) => post<Order>(`/orders/${orderId}/submit`, {}),
      cancel: (orderId: string) => post<Order>(`/orders/${orderId}/cancel`, {}),
    },

    // Payments
    payments: {
      create: (data: Pick<Payment, 'orderId' | 'method' | 'amount'>) =>
        post<Payment>('/payments', data),
      get: (id: string) => get<Payment>(`/payments/${id}`),
      listByOrder: (orderId: string) => get<Payment[]>(`/orders/${orderId}/payments`),
    },

    // Printers
    printers: {
      list: (locationId: string) => get<Printer[]>(`/locations/${locationId}/printers`),
      create: (data: Omit<Printer, 'id'>) => post<Printer>('/printers', data),
      update: (id: string, data: Partial<Printer>) => patch<Printer>(`/printers/${id}`, data),
      delete: (id: string) => del<void>(`/printers/${id}`),
    },

    // Staff
    staff: {
      list: (businessId: string) => get<User[]>(`/businesses/${businessId}/staff`),
      create: (data: Omit<User, 'id'> & { password?: string; pin?: string }) =>
        post<User>('/staff', data),
      update: (id: string, data: Partial<User>) => patch<User>(`/staff/${id}`, data),
    },

    // Reports
    reports: {
      summary: (locationId: string, period: 'today' | 'week' | 'month') =>
        get<ReportSummary>(`/locations/${locationId}/reports/summary?period=${period}`),
    },

    // AI
    ai: {      command: (data: AiCommandRequest) => post<AiCommandResponse>('/ai/command', data),
      confirm: (executionId: string) => post<{ success: boolean; message: string }>('/ai/confirm', { executionId }),
    },
  }
}

export type SmartServeApiClient = ReturnType<typeof createApiClient>
