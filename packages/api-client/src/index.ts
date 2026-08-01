import type {
  Business,
  Discount,
  Location,
  MenuCategory,
  MenuItem,
  ModifierGroup,
  Shift,
  Table,
  Order,
  OrderItem,
  Payment,
  Printer,
  PrinterRoute,
  User,
  TokenPair,
  AiCommandRequest,
  AiCommandResponse,
  MenuImportItem,
  MenuImportTurn,
  MenuImportApplyResponse,
  ApiError,
  ReportSummary,
} from '@smartserve/types'

// ─── Config ──────────────────────────────────────────────────────────────────

export interface ApiClientConfig {
  baseUrl: string
  getAccessToken: () => string | null
  /** Return the refresh token to enable automatic retry-on-401 token refresh. */
  getRefreshToken?: () => string | null
  /** Called with new tokens after a successful automatic refresh. */
  onTokensRefreshed?: (accessToken: string, refreshToken: string) => void
  onUnauthorized?: () => void
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

// Shared across concurrent requests so only one refresh happens at a time
let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(config: ApiClientConfig): Promise<boolean> {
  const refreshToken = config.getRefreshToken?.()
  if (!refreshToken || !config.onTokensRefreshed) return false

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${config.baseUrl}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken }),
        })
        if (!res.ok) return false
        const json = await res.json()
        const data = json.data ?? json
        config.onTokensRefreshed!(data.accessToken, data.refreshToken)
        return true
      } catch {
        return false
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

async function request<T>(
  config: ApiClientConfig,
  path: string,
  options: RequestInit = {},
  isRetry = false,
): Promise<T> {
  const token = config.getAccessToken()
  const isFormData = options.body instanceof FormData
  const headers: Record<string, string> = {
    // Let the browser set the multipart boundary itself for FormData bodies
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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
    if (!isRetry && !path.startsWith('/auth/') && (await tryRefresh(config))) {
      return request<T>(config, path, options, true)
    }
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
  const postForm = <T>(path: string, body: FormData) => request<T>(config, path, { method: 'POST', body })
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
      list: (locationId: string) => get<MenuCategory[]>(`/menu/locations/${locationId}/categories`),
      create: (data: Omit<MenuCategory, 'id'>) => post<MenuCategory>('/menu/categories', data),
      update: (id: string, data: Partial<MenuCategory>) =>
        patch<MenuCategory>(`/menu/categories/${id}`, data),
      delete: (id: string) => del<void>(`/menu/categories/${id}`),
      reorder: (locationId: string, ids: string[]) =>
        post<void>(`/menu/locations/${locationId}/categories/reorder`, { ids }),
    },

    // Menu Items
    menuItems: {
      list: (categoryId: string) => get<MenuItem[]>(`/menu/categories/${categoryId}/items`),
      get: (id: string) => get<MenuItem>(`/menu/items/${id}`),
      create: (data: Omit<MenuItem, 'id' | 'modifierGroups'>) =>
        post<MenuItem>('/menu/items', data),
      update: (id: string, data: Partial<MenuItem>) => patch<MenuItem>(`/menu/items/${id}`, data),
      delete: (id: string) => del<void>(`/menu/items/${id}`),
      setStock: (id: string, inStock: boolean) =>
        patch<MenuItem>(`/menu/items/${id}/stock`, { inStock }),
      listStock: (locationId: string) =>
        get<MenuItem[]>(`/menu/locations/${locationId}/stock`),
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
      applyDiscount: (orderId: string, code: string) =>
        post<Order>(`/orders/${orderId}/discount`, { code }),
      publicActive: (locationId: string) =>
        get<Order[]>(`/public/locations/${locationId}/orders`),
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
      listRoutes: (locationId: string) =>
        get<PrinterRoute[]>(`/locations/${locationId}/printer-routes`),
      addRoute: (printerId: string, itemId: string) =>
        post<PrinterRoute>('/printer-routes', { printerId, itemId }),
      deleteRoute: (routeId: string) => del<void>(`/printer-routes/${routeId}`),
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

    // Discounts
    discounts: {
      list: (businessId: string) => get<Discount[]>(`/businesses/${businessId}/discounts`),
      create: (data: Omit<Discount, 'id' | 'createdAt'>) => post<Discount>('/discounts', data),
      update: (id: string, data: Partial<Pick<Discount, 'name' | 'value' | 'minOrderAmount' | 'active' | 'expiresAt'>>) =>
        patch<Discount>(`/discounts/${id}`, data),
      delete: (id: string) => del<void>(`/discounts/${id}`),
    },

    // Shifts
    shifts: {
      open: (locationId: string, openingCash: number, notes?: string) =>
        post<Shift>(`/locations/${locationId}/shifts/open`, { openingCash, notes }),
      close: (shiftId: string, closingCash: number, notes?: string) =>
        post<Shift>(`/shifts/${shiftId}/close`, { closingCash, notes }),
      current: (locationId: string) =>
        get<Shift | null>(`/locations/${locationId}/shifts/current`),
      list: (locationId: string) =>
        get<Shift[]>(`/locations/${locationId}/shifts`),
    },

    // AI
    ai: {
      command: (data: AiCommandRequest) => post<AiCommandResponse>('/ai/command', data),
      confirm: (executionId: string) => post<{ success: boolean; message: string }>('/ai/confirm', { executionId }),
      importMenuFile: (locationId: string, file: File) => {
        const form = new FormData()
        form.append('location_id', locationId)
        form.append('file', file)
        return postForm<MenuImportTurn>('/ai/menu-import', form)
      },
      importMenuMessage: (sessionId: string, message: string) =>
        post<MenuImportTurn>('/ai/menu-import/message', { sessionId, message }),
      importMenuApply: (sessionId: string, items?: MenuImportItem[]) =>
        post<MenuImportApplyResponse>('/ai/menu-import/apply', { sessionId, items }),
    },
  }
}

export type SmartServeApiClient = ReturnType<typeof createApiClient>
