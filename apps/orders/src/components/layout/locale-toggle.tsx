'use client'

import { useLocale, useTranslations } from 'next-intl'
import { useRouter } from 'next/navigation'
import { useTransition } from 'react'
import { LanguageSwitcher, type AppLocale } from '@smartserve/ui'
import { setUserLocale } from '@/i18n/set-locale'

export function LocaleToggle() {
  const locale = useLocale() as AppLocale
  const t = useTranslations('common')
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  function onChange(next: AppLocale) {
    startTransition(async () => {
      await setUserLocale(next)
      router.refresh()
    })
  }

  return <LanguageSwitcher locale={locale} onChange={onChange} disabled={isPending} ariaLabel={t('language')} />
}
