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

async function expectNoHorizontalScroll(page: Page) {
  const extra = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(extra).toBeLessThanOrEqual(1)
}

test('orders top nav collapses Kitchen, Display and Logout on phones', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E nav')
  await pinLoginWaiter(page)

  await page.setViewportSize({ width: 1180, height: 820 })
  await expect(page.getByRole('link', { name: /תצוגת מטבח|Kitchen Display/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /תצוגת לקוחות|Customer Display/i })).toBeVisible()
  await expect(page.getByRole('button', { name: /יציאה|Logout/i })).toBeVisible()
  await expect(page.getByTestId('open-orders-menu')).toBeHidden()
  await expectNoHorizontalScroll(page)
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByTestId('open-orders-menu')).toBeVisible()
  await expect(page.getByRole('link', { name: /תצוגת מטבח|Kitchen Display/i })).toHaveCount(0)
  await page.getByTestId('open-orders-menu').click()
  await expect(page.getByTestId('orders-overflow-menu').getByRole('link', { name: /תצוגת מטבח|Kitchen Display/i })).toBeVisible()
  await expect(page.getByTestId('orders-overflow-menu').getByRole('link', { name: /תצוגת לקוחות|Customer Display/i })).toBeVisible()
  await expect(page.getByTestId('orders-overflow-menu').getByRole('button', { name: /יציאה|Logout/i })).toBeVisible()
  await expectNoHorizontalScroll(page)
  await test.info().attach('after-he-light-phone', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
