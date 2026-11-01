import { test, expect, type Page } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'
import { demoLocationId, registerPosDevice } from './owner-session'

const WAITER_PIN = '1234'

async function pinLoginWaiter(page: Page) {
  await page.goto('/login')
  await page.getByRole('button', { name: /Demo Waiter/i }).click()
  for (const digit of WAITER_PIN) {
    await page.getByRole('button', { name: digit, exact: true }).click()
  }
  await expect(page).toHaveURL(/\/orders/)
}

test('floor plan shows live table cards', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E floor')
  await pinLoginWaiter(page)
  await page.goto('/tables')
  await expect(page.getByRole('heading', { name: /תכנית|Floor/i })).toBeVisible()
  await expect(page.getByTestId('table-card').first()).toBeVisible()
  await expect(page.getByTestId('table-card').first()).toHaveAttribute('data-floor-state', /.*/)
  await expect(page.getByRole('button', { name: /עריכת מפה|Edit layout/i })).toHaveCount(0)
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
