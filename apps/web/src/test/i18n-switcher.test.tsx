import { describe, it, expect } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { SalesReportView } from '@/app/(dashboard)/reports/components/sales-report-view'
import enMessages from '@/messages/en.json'
import heMessages from '@/messages/he.json'
import type { SalesReport } from '@smartserve/types'

function renderWithLocale(locale: 'en' | 'he', ui: React.ReactElement) {
  const messages = locale === 'en' ? enMessages : heMessages
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  )
}

// groupLabel here is user-entered business data (a menu item name) — it must never be
// translated, regardless of the active locale.
const report: SalesReport = {
  groupBy: 'item',
  start: '2026-01-01T00:00:00.000Z',
  end: '2026-01-31T23:59:59.999Z',
  rows: [{ groupId: 'item-1', groupLabel: 'Burger', qty: 5, revenue: 250 }],
  totalQty: 5,
  totalRevenue: 250,
}

describe('language switcher: app vocabulary vs. user-entered content', () => {
  it('renders English app vocabulary and the item name as-is', () => {
    renderWithLocale('en', <SalesReportView report={report} />)

    // App vocabulary — translated.
    expect(screen.getByText('Qty sold')).toBeInTheDocument()
    expect(screen.getByText('Revenue (incl. VAT)')).toBeInTheDocument()

    // User-entered business data — never translated, rendered verbatim.
    expect(screen.getByText('Burger')).toBeInTheDocument()

    cleanup()
  })

  it('switches app vocabulary to Hebrew while leaving the item name unchanged', () => {
    renderWithLocale('he', <SalesReportView report={report} />)

    // App vocabulary — now in Hebrew.
    expect(screen.getByText('כמות שנמכרה')).toBeInTheDocument()
    expect(screen.getByText('הכנסות (כולל מע״מ)')).toBeInTheDocument()

    // English app-vocabulary strings must be gone now that the locale switched.
    expect(screen.queryByText('Qty sold')).not.toBeInTheDocument()
    expect(screen.queryByText('Revenue (incl. VAT)')).not.toBeInTheDocument()

    // User-entered business data is identical regardless of locale — never translated.
    expect(screen.getByText('Burger')).toBeInTheDocument()

    cleanup()
  })
})
