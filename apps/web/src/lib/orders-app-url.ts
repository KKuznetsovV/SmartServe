const DEFAULT_ORDERS_APP_URL = 'http://localhost:3001'

export function ordersAppUrl(path: string): string {
  const base = (process.env.NEXT_PUBLIC_ORDERS_URL ?? DEFAULT_ORDERS_APP_URL).replace(/\/$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}
