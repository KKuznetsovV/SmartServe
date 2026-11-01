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

async function expectNoHorizontalScroll(page: Page) {
  const extra = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(extra).toBeLessThanOrEqual(1)
}

test('admin dashboard is a drawer on phone and a sidebar on tablet', async ({ page }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await login(page)

  await page.setViewportSize({ width: 1180, height: 820 })
  await page.goto('/dashboard')
  await expect(page.getByTestId('admin-sidebar')).toBeVisible()
  await expect(page.getByTestId('open-admin-menu')).toHaveCount(0)
  await expectNoHorizontalScroll(page)
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByTestId('open-admin-menu')).toBeVisible()
  await expect(page.getByTestId('admin-sidebar-drawer')).toHaveCount(0)
  await page.getByTestId('open-admin-menu').click()
  await expect(page.getByTestId('admin-sidebar-drawer')).toBeVisible()
  await expect(page.getByRole('link', { name: /לוח בקרה|Dashboard/i })).toBeVisible()
  const menu = page.getByTestId('open-admin-menu')
  const box = await menu.boundingBox()
  expect(box).not.toBeNull()
  if (box) {
    expect(box.height).toBeGreaterThanOrEqual(48)
    expect(box.width).toBeGreaterThanOrEqual(48)
  }
  await expectNoHorizontalScroll(page)
  await test.info().attach('after-he-light-phone', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('admin dashboard English dark phone', async ({ page }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  await login(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/dashboard')
  await expect(page.getByTestId('open-admin-menu')).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-en-dark-phone', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
