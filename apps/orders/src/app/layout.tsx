import type { Metadata } from 'next'
import { NextIntlClientProvider } from 'next-intl'
import { getLocale, getMessages } from 'next-intl/server'
import { getNoFlashThemeScript } from '@smartserve/ui'
import { Providers } from '@/components/providers'
import { getUserTheme } from '@/theme/get-theme'
import './globals.css'

export const metadata: Metadata = {
  title: 'SmartServe — ניהול מסעדה חכם',
  description: 'מערכת קופה חכמה לניהול מסעדות',
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale()
  const messages = await getMessages()
  const dir = locale === 'he' ? 'rtl' : 'ltr'
  const theme = await getUserTheme()

  return (
    <html lang={locale} dir={dir} className={theme === 'dark' ? 'dark' : undefined} suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        <script dangerouslySetInnerHTML={{ __html: getNoFlashThemeScript(theme) }} />
        <NextIntlClientProvider messages={messages}>
          <Providers>{children}</Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}
