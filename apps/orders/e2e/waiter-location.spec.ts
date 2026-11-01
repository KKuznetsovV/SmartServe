import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { demoLocationId, registerPosDevice } from './owner-session'

const WAITER_PIN = '1234'

async function pinLoginWaiter(page: Page, request: APIRequestContext) {
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E waiter location')
  await page.goto('/login')
  await page.getByRole('button', { name: /Demo Waiter/i }).click()
  await page.keyboard.type(WAITER_PIN)
  await expect(page).toHaveURL(/\/orders/)
}

test('waiter load uses the device location and never 403s', async ({ page, request }) => {
  test.setTimeout(60_000)
  const forbidden: string[] = []
  page.on('response', (response) => {
    if (response.status() === 403) forbidden.push(response.url())
  })
  await pinLoginWaiter(page, request)
  await expect(page.getByRole('heading', { name: /הזמנות|Orders/i })).toBeVisible()
  await page.goto('/tables')
  await expect(page.getByRole('heading', { name: /תכנית שולחנות|Floor Plan/i })).toBeVisible()
  expect(forbidden, forbidden.join('\n')).toEqual([])
})
