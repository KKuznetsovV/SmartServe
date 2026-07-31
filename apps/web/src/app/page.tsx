import { useTranslations } from 'next-intl'

export default function HomePage() {
  const t = useTranslations('nav')
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold text-primary mb-4">SmartServe</h1>
      <p className="text-muted-foreground text-lg">{t('dashboard')}</p>
    </main>
  )
}
