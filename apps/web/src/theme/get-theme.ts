import { cookies } from 'next/headers'
import type { ThemePreference } from '@smartserve/ui'

export async function getUserTheme(): Promise<ThemePreference> {
  const cookieStore = await cookies()
  const value = cookieStore.get('theme')?.value
  return value === 'dark' ? 'dark' : 'light'
}
