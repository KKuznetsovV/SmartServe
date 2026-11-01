import { test, expect, type Page } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'

const EMAIL = 'owner@demo.com'
const PASSWORD = 'demo1234'

async function login(page: Page) {
  await page.goto('/login')
  await page.locator('#email').fill(EMAIL)
  await page.locator('#password').fill(PASSWORD)
  await page.locator('form').getByRole('button').click()
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 })
}

test('web login has landmarks and no serious axe issues', async ({ page }) => {
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await page.goto('/login')
  await expect(page.getByRole('main')).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: 'SmartServe' })).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('dashboard, menu, staff, printers and stock pass axe in light and dark', async ({ page }) => {
  test.setTimeout(120_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await login(page)

  for (const path of ['/dashboard', '/menu', '/staff', '/printers', '/stock', '/settings']) {
    await page.goto(path)
    await expect(page.getByRole('heading').first()).toBeVisible()
    await expectNoSeriousAxeViolations(page)
  }
  await test.info().attach('after-he-light-menu', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })

  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  for (const path of ['/dashboard', '/menu', '/staff', '/printers', '/stock']) {
    await page.goto(path)
    await expect(page.locator('html')).toHaveClass(/dark/)
    await expect(page.getByRole('heading').first()).toBeVisible()
    await expectNoSeriousAxeViolations(page)
  }
  await test.info().attach('after-en-dark-staff', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
