import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NextIntlClientProvider } from 'next-intl'
import { OrderOverflowMenu } from '@/app/(app)/orders/[orderId]/order-overflow-menu'
import enMessages from '@/messages/en.json'

describe('OrderOverflowMenu', () => {
  it('hides cancel behind a confirmation dialog', async () => {
    const onCancel = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    render(
      <NextIntlClientProvider locale="en" messages={enMessages}>
        <OrderOverflowMenu canCancel cancelPending={false} onCancel={onCancel} />
      </NextIntlClientProvider>,
    )

    expect(screen.queryByRole('menuitem', { name: /Cancel Order/i })).not.toBeInTheDocument()
    await user.click(screen.getByTestId('order-overflow'))
    await user.click(screen.getByRole('menuitem', { name: /Cancel Order/i }))
    expect(onCancel).not.toHaveBeenCalled()
    await user.click(screen.getByTestId('confirm-cancel-order'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})
