'use server'

import { cookies } from 'next/headers'

const THEME_COOKIE = 'theme'
const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365

export async function setUserTheme(theme: 'light' | 'dark' | 'system') {
  const cookieStore = await cookies()
  cookieStore.set(THEME_COOKIE, theme, { maxAge: ONE_YEAR_SECONDS, path: '/' })
}
