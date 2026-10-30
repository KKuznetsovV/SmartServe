import { getRequestConfig } from 'next-intl/server'
import { cookies } from 'next/headers'
import { resolveAppLocale } from '@smartserve/ui'

export default getRequestConfig(async () => {
  const cookieStore = await cookies()
  const locale = resolveAppLocale(cookieStore.get('locale')?.value)

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  }
})
