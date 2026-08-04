export interface ApiClientConfig {
  baseUrl: string
  getAccessToken: () => string | null
  /** Return the refresh token to enable automatic retry-on-401 token refresh. */
  getRefreshToken?: () => string | null
  /** Called with new tokens after a successful automatic refresh. */
  onTokensRefreshed?: (accessToken: string, refreshToken: string) => void
  onUnauthorized?: () => void
}

export interface Http {
  get: <T>(path: string) => Promise<T>
  post: <T>(path: string, body: unknown) => Promise<T>
  postForm: <T>(path: string, body: FormData) => Promise<T>
  put: <T>(path: string, body: unknown) => Promise<T>
  patch: <T>(path: string, body: unknown) => Promise<T>
  del: <T>(path: string) => Promise<T>
}

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
    const body = await response.json().catch(() => null)
    // FastAPI's default error shape is { detail: string | { msg }[] }; also
    // support { error: { message } } in case a handler ever returns that instead.
    let message = `HTTP ${response.status}`
    if (typeof body?.error?.message === 'string') {
      message = body.error.message
    } else if (typeof body?.detail === 'string') {
      message = body.detail
    } else if (Array.isArray(body?.detail)) {
      const joined = body.detail
        .map((d: { msg?: string }) => d.msg)
        .filter(Boolean)
        .join('; ')
      if (joined) message = joined
    }
    throw new Error(message)
  }

  // 204 No Content
  if (response.status === 204) return undefined as T

  const json = await response.json()
  return (json.data ?? json) as T
}

export function createHttp(config: ApiClientConfig): Http {
  return {
    get: (path) => request(config, path),
    post: (path, body) => request(config, path, { method: 'POST', body: JSON.stringify(body) }),
    postForm: (path, body) => request(config, path, { method: 'POST', body }),
    put: (path, body) => request(config, path, { method: 'PUT', body: JSON.stringify(body) }),
    patch: (path, body) => request(config, path, { method: 'PATCH', body: JSON.stringify(body) }),
    del: (path) => request(config, path, { method: 'DELETE' }),
  }
}
