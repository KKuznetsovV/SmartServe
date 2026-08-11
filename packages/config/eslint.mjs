import { FlatCompat } from '@eslint/eslintrc'

/**
 * Shared Next.js ESLint flat config, used by every app in this monorepo.
 * `baseDirectory` must be the consuming app's own directory so `next/core-web-vitals`
 * resolves relative to that app's installed dependencies.
 */
export function nextConfig(baseDirectory) {
  const compat = new FlatCompat({ baseDirectory })

  return [
    ...compat.extends('next/core-web-vitals'),
    {
      ignores: ['.next/', 'node_modules/'],
    },
  ]
}
