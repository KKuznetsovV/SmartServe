export interface ApiClientConfig {
  baseUrl: string
  getAccessToken: () => string | null
  /** Called with the new access token after a successful cookie-based refresh. */
  onTokensRefreshed?: (accessToken: string) => void
  onUnauthorized?: () => void
}

export interface Http {
  get: <T>(path: string, extraHeaders?: Record<string, string>) => Promise<T>
  post: <T>(path: string, body: unknown, extraHeaders?: Record<string, string>) => Promise<T>
  postForm: <T>(path: string, body: FormData) => Promise<T>
  put: <T>(path: string, body: unknown) => Promise<T>
  patch: <T>(path: string, body: unknown) => Promise<T>
  del: <T>(path: string) => Promise<T>
  /** For binary downloads (e.g. CSV export) — bypasses JSON parsing and
   * surfaces the server-provided filename from Content-Disposition. */
  getBlob: (path: string) => Promise<{ blob: Blob; filename: string | null }>
}

// Shared across concurrent requests so only one refresh happens at a time
let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(config: ApiClientConfig): Promise<boolean> {
  if (!config.onTokensRefreshed) return false

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${config.baseUrl}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        })
        if (!res.ok) return false
        const json = await res.json()
        const data = json.data ?? json
        config.onTokensRefreshed!(data.accessToken)
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

async function fetchAuthed(
  config: ApiClientConfig,
  path: string,
  options: RequestInit = {},
  isRetry = false,
): Promise<Response> {
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
    credentials: 'include',
    headers,
  })

  if (response.status === 401) {
    const skipRefresh =
      path === '/auth/refresh' ||
      path === '/auth/login' ||
      path === '/auth/pin' ||
      path === '/auth/logout'
    if (!isRetry && !skipRefresh && (await tryRefresh(config))) {
      return fetchAuthed(config, path, options, true)
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

  return response
}

async function request<T>(
  config: ApiClientConfig,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetchAuthed(config, path, options)

  // 204 No Content
  if (response.status === 204) return undefined as T

  const json = await response.json()
  return (json.data ?? json) as T
}

function parseFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) return null
  const match = /filename="?([^";]+)"?/.exec(contentDisposition)
  return match ? match[1] : null
}

async function requestBlob(
  config: ApiClientConfig,
  path: string,
): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetchAuthed(config, path)
  const blob = await response.blob()
  return { blob, filename: parseFilename(response.headers.get('Content-Disposition')) }
}

export function createHttp(config: ApiClientConfig): Http {
  return {
    get: (path, extraHeaders) => request(config, path, { headers: extraHeaders }),
    post: (path, body, extraHeaders) =>
      request(config, path, { method: 'POST', body: JSON.stringify(body), headers: extraHeaders }),
    postForm: (path, body) => request(config, path, { method: 'POST', body }),
    put: (path, body) => request(config, path, { method: 'PUT', body: JSON.stringify(body) }),
    patch: (path, body) => request(config, path, { method: 'PATCH', body: JSON.stringify(body) }),
    del: (path) => request(config, path, { method: 'DELETE' }),
    getBlob: (path) => requestBlob(config, path),
  }
}
