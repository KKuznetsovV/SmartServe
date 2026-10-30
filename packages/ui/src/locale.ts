export const APP_LOCALES = ['he', 'en'] as const

export type AppLocale = (typeof APP_LOCALES)[number]

const FALLBACK_LOCALE: AppLocale = 'he'

export function resolveAppLocale(value: string | null | undefined): AppLocale {
  return APP_LOCALES.includes(value as AppLocale) ? (value as AppLocale) : FALLBACK_LOCALE
}
