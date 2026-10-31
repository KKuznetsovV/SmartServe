'use client'

import { useTranslations } from 'next-intl'
import { ThemeToggle as ThemeToggleControl, useThemeToggle } from '@smartserve/ui'
import { setUserTheme } from '@/theme/set-theme'

export function ThemeToggle({ className }: { className?: string }) {
  const t = useTranslations('common')
  const { theme, setTheme } = useThemeToggle(setUserTheme)

  return (
    <ThemeToggleControl
      theme={theme}
      onChange={setTheme}
      ariaLabel={t('theme')}
      labels={{ light: t('themeLight'), dark: t('themeDark') }}
      className={className}
    />
  )
}
