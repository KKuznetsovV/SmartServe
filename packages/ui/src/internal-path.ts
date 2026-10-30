/**
 * Accept only same-origin relative paths for post-login redirects.
 * Rejects protocol-relative URLs and anything that is not a path.
 */
export function safeInternalPath(raw: string | null | undefined, fallback: string): string {
  if (!raw) return fallback
  if (!raw.startsWith('/')) return fallback
  if (raw.startsWith('//')) return fallback
  if (raw.includes('://')) return fallback
  return raw
}

export function withLoginNext(loginPath: string, next: string): string {
  const encoded = encodeURIComponent(next)
  const sep = loginPath.includes('?') ? '&' : '?'
  return `${loginPath}${sep}next=${encoded}`
}
