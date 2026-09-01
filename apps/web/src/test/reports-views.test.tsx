import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { SalesReportView } from '@/app/(dashboard)/reports/components/sales-report-view'
import { ServerSalesReportView } from '@/app/(dashboard)/reports/components/server-sales-report-view'
import { ClosedOrdersReportView } from '@/app/(dashboard)/reports/components/closed-orders-report-view'
import type { SalesReport, ServerSalesReport, ClosedOrdersReport } from '@smartserve/types'
import messages from '@/messages/en.json'

function renderWithIntl(ui: React.ReactElement) {
  return render(
    <NextIntlClientProvider locale="en" messages={messages}>
      {ui}
    </NextIntlClientProvider>,
  )
}


describe('SalesReportView', () => {
  it('renders grouped rows and totals', () => {
    const report: SalesReport = {
      groupBy: 'item',
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      rows: [{ groupId: 'item-1', groupLabel: 'Burger', qty: 5, revenue: 250 }],
      totalQty: 5,
      totalRevenue: 250,
    }
    renderWithIntl(<SalesReportView report={report} />)
    expect(screen.getByText('Burger')).toBeInTheDocument()
  })

  it('shows an empty state when there are no rows', () => {
    const report: SalesReport = {
      groupBy: 'menu',
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      rows: [],
      totalQty: 0,
      totalRevenue: 0,
    }
    renderWithIntl(<SalesReportView report={report} />)
    expect(screen.getByText(/no sales in this range/i)).toBeInTheDocument()
  })
})

describe('ServerSalesReportView', () => {
  it('shows the qty column only when filtered by item/category', () => {
    const filtered: ServerSalesReport = {
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      itemId: 'item-1',
      categoryId: null,
      rows: [{ serverId: 's-1', serverName: 'Alice', orderCount: 3, qty: 7, revenue: 140 }],
    }
    renderWithIntl(<ServerSalesReportView report={filtered} />)
    expect(screen.getByText('Alice')).toBeInTheDocument()
    expect(screen.getByText('Qty')).toBeInTheDocument()
  })

  it('omits the qty column when unfiltered', () => {
    const unfiltered: ServerSalesReport = {
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      itemId: null,
      categoryId: null,
      rows: [{ serverId: 's-1', serverName: 'Alice', orderCount: 3, qty: null, revenue: 140 }],
    }
    renderWithIntl(<ServerSalesReportView report={unfiltered} />)
    expect(screen.queryByText('Qty')).not.toBeInTheDocument()
  })
})

describe('ClosedOrdersReportView', () => {
  it('renders order rows with status badges', () => {
    const report: ClosedOrdersReport = {
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      status: null,
      orders: [
        {
          id: 'order-12345678',
          status: 'paid',
          channel: 'dine_in',
          total: 99.5,
          createdBy: 'user-1',
          createdByName: 'Bob',
          createdAt: '2026-01-15T12:00:00.000Z',
        },
      ],
    }
    renderWithIntl(<ClosedOrdersReportView report={report} />)
    expect(screen.getByText('Bob')).toBeInTheDocument()
    expect(screen.getByText('Paid')).toBeInTheDocument()
  })

  it('shows an empty state when there are no closed orders', () => {
    const report: ClosedOrdersReport = {
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      status: 'cancelled',
      orders: [],
    }
    renderWithIntl(<ClosedOrdersReportView report={report} />)
    expect(screen.getByText(/no closed orders in this range/i)).toBeInTheDocument()
  })
})
