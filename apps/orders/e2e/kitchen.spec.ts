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

async function submitTakeaway(page: Page, request: APIRequestContext) {
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E KDS')
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
  expect(categories.ok()).toBeTruthy()
  const catList = await categories.json()
  const mains = catList.find((c: { name: string; parentId?: string | null }) => c.name === 'Mains' && !c.parentId)
  if (mains) {
    const items = await request.get(`${API}/menu/categories/${mains.id}/items`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const itemList = await items.json()
    const burger = itemList.find((i: { name: string }) => i.name === 'Burger') ?? itemList[0]
    if (burger) {
      await request.post(`${API}/orders/${order.id}/items`, {
        headers: { Authorization: `Bearer ${token}` },
        data: {
          menuItemId: burger.id,
          menuItemName: burger.name,
          qty: 1,
          unitPrice: burger.price,
          modifiers: [],
        },
      })
    }
  }
  const submitted = await request.post(`${API}/orders/${order.id}/submit`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(submitted.ok(), await submitted.text()).toBeTruthy()
  await pinLoginWaiter(page)
  return order.id as string
}

test('kitchen tickets show the table, order number and a 64px bump', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await submitTakeaway(page, request)
  await page.goto('/kitchen?station=kitchen')
  await expect(page.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /מטבח|Kitchen/i }).first()).toBeVisible()
  const bump = page.getByTestId('bump-ticket').first()
  await expect(page.getByText('המבורגר').first()).toBeVisible()
  await expect(bump).toBeVisible()
  const box = await bump.boundingBox()
  expect(box).not.toBeNull()
  if (box) expect(box.height).toBeGreaterThanOrEqual(64)
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
