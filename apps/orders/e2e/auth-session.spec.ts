import { test, expect, type Page } from '@playwright/test'
import { demoLocationId, registerPosDevice } from './owner-session'

const WAITER_PIN = '1234'

async function pinLoginWaiter(page: Page) {
  await page.goto('/login')
  await page.getByRole('button', { name: /Demo Waiter/i }).click()
  for (const digit of WAITER_PIN) {
    await page.getByRole('button', { name: digit, exact: true }).click()
  }
}

test('reload and a new tab keep the session on /kitchen', async ({ page, context, request }) => {
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E POS')
  await pinLoginWaiter(page)
  await expect(page).toHaveURL(/\/orders/)

  await page.goto('/kitchen')
  await expect(page.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()

  await page.reload()
  await expect(page).toHaveURL(/\/kitchen/)
  await expect(page.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()

  const tab = await context.newPage()
  await tab.goto('/kitchen')
  await expect(tab).toHaveURL(/\/kitchen/)
  await expect(tab.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()
  await tab.close()
})

test('PIN session survives reload and logout returns to login', async ({ page, request }) => {
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E POS')
  await pinLoginWaiter(page)
  await expect(page).toHaveURL(/\/orders/)

  await page.reload()
  await expect(page).toHaveURL(/\/orders/)

  await page.getByRole('button', { name: /יציאה|התנתק|Log out|Logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByRole('button', { name: /Demo Waiter/i })).toBeVisible()
})
