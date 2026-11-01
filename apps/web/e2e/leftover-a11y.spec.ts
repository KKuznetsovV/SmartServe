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
  await expect(page.getByRole('heading', { name: 'SmartServe' })).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('dashboard, printers and settings have no serious axe issues', async ({ page }) => {
  test.setTimeout(90_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await login(page)

  await page.goto('/dashboard')
  await expect(page.getByRole('heading').first()).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-dashboard', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })

  await page.goto('/printers')
  await expect(page.getByRole('heading', { name: /מדפסות|Printers/i })).toBeVisible()
  await expectNoSeriousAxeViolations(page)

  await page.goto('/settings')
  await expect(page.getByRole('heading').first()).toBeVisible()
  await expectNoSeriousAxeViolations(page)
})

test('dashboard English dark has no serious axe issues', async ({ page }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await login(page)
  await page.goto('/dashboard')
  await expect(page.getByRole('heading').first()).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-en-dark-dashboard', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
