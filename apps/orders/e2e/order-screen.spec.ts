import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'
import { API, demoLocationId, ownerToken, registerPosDevice } from './owner-session'

const WAITER_PIN = '1234'

async function pinLoginWaiter(page: Page) {
  await page.goto('/login')
  await page.getByRole('button', { name: /Demo Waiter/i }).click()
  for (const digit of WAITER_PIN) {
    await page.getByRole('button', { name: digit, exact: true }).click()
  }
  await expect(page).toHaveURL(/\/orders/)
}

async function openTakeawayOrder(page: Page, request: APIRequestContext) {
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E order screen')
  const token = await ownerToken(request)
  const created = await request.post(`${API}/orders`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { locationId, channel: 'takeaway' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const order = await created.json()
  const categories = await request.get(`${API}/menu/locations/${locationId}/categories`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(categories.ok(), await categories.text()).toBeTruthy()
  const catList = await categories.json()
  const starter = catList.find((c: { name: string; parentId?: string | null }) => c.name === 'Starters' && !c.parentId)
  if (starter) {
    const items = await request.get(`${API}/menu/categories/${starter.id}/items`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(items.ok(), await items.text()).toBeTruthy()
    const itemList = await items.json()
    const hummus = itemList.find((i: { name: string }) => i.name === 'Hummus') ?? itemList[0]
    if (hummus) {
      const added = await request.post(`${API}/orders/${order.id}/items`, {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          menuItemId: hummus.id,
          menuItemName: hummus.name,
          qty: 1,
          unitPrice: hummus.price,
          modifiers: [],
        },
      })
      expect(added.ok(), await added.text()).toBeTruthy()
    }
  }
  await pinLoginWaiter(page)
  await page.goto(`/orders/${order.id}`)
  await expect(page.getByRole('heading', { name: /הזמנה|Order/i })).toBeVisible()
  return order.id as string
}

test('order screen localizes tiles and keeps cancel in an overflow menu', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await openTakeawayOrder(page, request)

  await expect(page.getByTestId('menu-root').filter({ hasText: 'ראשונות' }).first()).toBeVisible()
  const hebrewTile = page.getByTestId('menu-tile').filter({ hasText: /[\u0590-\u05FF]/ })
  const tile = (await hebrewTile.count()) > 0 ? hebrewTile.first() : page.getByTestId('menu-tile').first()
  await expect(tile).toBeVisible()
  await expect(tile).toContainText(/₪|ILS|\d/)
  const box = await tile.boundingBox()
  expect(box).not.toBeNull()
  if (box) expect(box.height).toBeGreaterThanOrEqual(64)

  await expect(page.getByText(/לא נשלח|Not sent/)).toBeVisible()
  await expect(page.getByText('חומוס').first()).toBeVisible()
  await expectNoSeriousAxeViolations(page)

  await page.getByTestId('order-overflow').click({ force: true })
  await page.getByRole('menuitem', { name: /בטל הזמנה/ }).click()
  await expect(page.getByTestId('confirm-cancel-order')).toBeVisible()

  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('order screen stays usable on a phone in English dark mode', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 390, height: 844 })
  await openTakeawayOrder(page, request)
  await expect(page.getByTestId('menu-tile').first()).toBeVisible()
  const overflow = page.getByTestId('order-overflow')
  const box = await overflow.boundingBox()
  expect(box).not.toBeNull()
  if (box) {
    expect(box.height).toBeGreaterThanOrEqual(48)
    expect(box.width).toBeGreaterThanOrEqual(48)
  }
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-en-dark-phone', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
