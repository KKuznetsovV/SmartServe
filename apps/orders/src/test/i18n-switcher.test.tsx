import { describe, it, expect } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { ItemConfigDialog } from '@/app/(app)/orders/[orderId]/item-config-dialog'
import enMessages from '@/messages/en.json'
import heMessages from '@/messages/he.json'
import type { MenuItem } from '@smartserve/types'

function renderWithLocale(locale: 'en' | 'he', ui: React.ReactElement) {
  const messages = locale === 'en' ? enMessages : heMessages
  return render(
    <NextIntlClientProvider locale={locale} messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  )
}

// A menu item with a modifier group — deliberately named in a way that would never
// match a real translation key, so any appearance in the rendered output can only be
// because the component rendered the raw, untranslated business data.
const item: MenuItem = {
  id: '11111111-1111-1111-1111-111111111111',
  categoryId: '22222222-2222-2222-2222-222222222222',
  name: 'Margherita Pizza',
  price: 42,
  taxRate: 0.17,
  preparationTimeMin: 10,
  sortOrder: 0,
  active: true,
  inStock: true,
  defaultFireCourse: 1,
  modifierGroups: [
    {
      id: '33333333-3333-3333-3333-333333333333',
      itemId: '11111111-1111-1111-1111-111111111111',
      name: 'Size',
      required: true,
      minSelect: 1,
      maxSelect: 1,
      modifiers: [
        {
          id: '44444444-4444-4444-4444-444444444444',
          groupId: '33333333-3333-3333-3333-333333333333',
          name: 'Small',
          priceDelta: 0,
          active: true,
        },
      ],
    },
  ],
}

describe('language switcher: app vocabulary vs. user-entered content', () => {
  it('renders English app vocabulary and the item/modifier names as-is', () => {
    renderWithLocale(
      'en',
      <ItemConfigDialog open item={item} onOpenChange={() => {}} onConfirm={() => {}} />,
    )

    // App vocabulary — translated.
    expect(screen.getByText('Quantity')).toBeInTheDocument()
    expect(screen.getByText('Notes (optional)')).toBeInTheDocument()
    expect(screen.getByText('Fire Course')).toBeInTheDocument()
    expect(screen.getByText('choose one')).toBeInTheDocument()

    // User-entered business data — never translated, rendered verbatim.
    expect(screen.getByText('Margherita Pizza')).toBeInTheDocument()
    expect(screen.getByText(/Size/)).toBeInTheDocument()
    expect(screen.getByText('Small')).toBeInTheDocument()

    cleanup()
  })

  it('switches app vocabulary to Hebrew while leaving item/modifier names unchanged', () => {
    renderWithLocale(
      'he',
      <ItemConfigDialog open item={item} onOpenChange={() => {}} onConfirm={() => {}} />,
    )

    // App vocabulary — now in Hebrew.
    expect(screen.getByText('כמות')).toBeInTheDocument()
    expect(screen.getByText('הערות (אופציונלי)')).toBeInTheDocument()
    expect(screen.getByText('שלח מנה')).toBeInTheDocument()
    expect(screen.getByText('בחר/י אחד')).toBeInTheDocument()

    // English app-vocabulary strings must be gone now that the locale switched.
    expect(screen.queryByText('Quantity')).not.toBeInTheDocument()
    expect(screen.queryByText('Notes (optional)')).not.toBeInTheDocument()

    // User-entered business data is identical regardless of locale — never translated.
    expect(screen.getByText('Margherita Pizza')).toBeInTheDocument()
    expect(screen.getByText(/Size/)).toBeInTheDocument()
    expect(screen.getByText('Small')).toBeInTheDocument()

    cleanup()
  })
})
