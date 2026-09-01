'use server'

import { cookies } from 'next/headers'

const LOCALE_COOKIE = 'locale'
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365

export async function setUserLocale(locale: 'he' | 'en') {
  const cookieStore = await cookies()
  cookieStore.set(LOCALE_COOKIE, locale, { maxAge: ONE_YEAR_SECONDS, path: '/' })
}
