import { test, expect, type APIRequestContext } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'
import { API, demoLocationId, ownerToken, registerDevice } from './owner-session'

async function addBurgerAndSubmit(
  request: APIRequestContext,
  token: string,
  locationId: string,
  itemStatus: 'preparing' | 'ready',
): Promise<number> {
  const created = await request.post(`${API}/orders`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { locationId, channel: 'takeaway' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const order = await created.json()
  const categories = await request.get(`${API}/menu/locations/${locationId}/categories`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  const catList = await categories.json()
  const mains = catList.find((c: { name: string; parentId?: string | null }) => c.name === 'Mains' && !c.parentId)
  if (mains) {
    const items = await request.get(`${API}/menu/categories/${mains.id}/items`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const itemList = await items.json()
    const burger = itemList.find((i: { name: string }) => i.name === 'Burger') ?? itemList[0]
    if (burger) {
      const added = await request.post(`${API}/orders/${order.id}/items`, {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          menuItemId: burger.id,
          menuItemName: burger.name,
          qty: 1,
          unitPrice: burger.price,
          modifiers: [],
        },
      })
      expect(added.ok(), await added.text()).toBeTruthy()
      const line = await added.json()
      const submitted = await request.post(`${API}/orders/${order.id}/submit`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      expect(submitted.ok(), await submitted.text()).toBeTruthy()
      const bumped = await request.patch(`${API}/orders/${order.id}/items/${line.id}/status`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { status: itemStatus },
      })
      expect(bumped.ok(), await bumped.text()).toBeTruthy()
    }
  }
  const latest = await request.get(`${API}/orders/${order.id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  const body = await latest.json()
  return body.orderNumber as number
}

test('customer display without a paired device goes to setup', async ({ page }) => {
  await page.goto('/display')
  await expect(page).toHaveURL(/setup/)
})

test('customer display shows preparing and ready columns', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  const locationId = await demoLocationId(request)
  const token = await ownerToken(request)
  await registerDevice(page, request, locationId, 'E2E display', 'display')
  const preparingNumber = await addBurgerAndSubmit(request, token, locationId, 'preparing')
  const readyNumber = await addBurgerAndSubmit(request, token, locationId, 'ready')
  await page.goto('/display')
  await expect(page.getByRole('heading', { name: /סטטוס הזמנה|Order Status/i })).toBeVisible()
  await expect(page.getByTestId('display-preparing')).toBeVisible()
  await expect(page.getByTestId('display-ready')).toBeVisible()
  await expect(
    page.getByTestId('display-preparing').locator(`[data-order-number="${preparingNumber}"]`),
  ).toBeVisible()
  await expect(page.getByTestId('display-ready').locator(`[data-order-number="${readyNumber}"]`)).toBeVisible()
  const readyBox = await page
    .getByTestId('display-ready')
    .locator(`[data-order-number="${readyNumber}"]`)
    .boundingBox()
  expect(readyBox).not.toBeNull()
  if (readyBox) expect(readyBox.height).toBeGreaterThanOrEqual(96)
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('customer display English dark tablet', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  const locationId = await demoLocationId(request)
  await registerDevice(page, request, locationId, 'E2E display en', 'display')
  await page.goto('/display')
  await expect(page.getByRole('heading', { name: /Order Status/i })).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-en-dark-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
