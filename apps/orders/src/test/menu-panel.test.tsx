import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { MenuPanel } from '@/app/(app)/orders/[orderId]/menu-panel'
import heMessages from '@/messages/he.json'
import type { MenuCategory, MenuItem } from '@smartserve/types'

vi.mock('@dnd-kit/core', () => ({
  useDraggable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => {},
    isDragging: false,
  }),
}))

vi.mock('@/hooks/use-menu', () => ({
  useCategories: () => ({
    data: [
      {
        id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        locationId: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        name: 'Drinks',
        nameHe: 'שתייה',
        sortOrder: 0,
        active: true,
      },
    ] satisfies MenuCategory[],
    isLoading: false,
  }),
  useMenuItems: () => ({
    data: [
      {
        id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
        categoryId: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        name: 'Cola',
        nameHe: 'קולה',
        price: 12,
        taxRate: 0.18,
        preparationTimeMin: 1,
        sortOrder: 0,
        active: true,
        inStock: true,
        defaultFireCourse: 1,
        modifierGroups: [],
      },
    ] satisfies MenuItem[],
    isLoading: false,
  }),
}))

describe('MenuPanel', () => {
  it('shows Hebrew catalog names and prices on tiles', () => {
    render(
      <NextIntlClientProvider locale="he" messages={heMessages}>
        <MenuPanel locationId="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" onItemTap={() => {}} />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole('button', { name: /שתייה/ })).toBeInTheDocument()
    expect(screen.getByText('קולה')).toBeInTheDocument()
    expect(screen.queryByText('Cola')).not.toBeInTheDocument()
    const tile = screen.getByTestId('menu-tile')
    expect(tile.className).toMatch(/min-h-16/)
    expect(tile.textContent).toMatch(/12/)
  })
})
