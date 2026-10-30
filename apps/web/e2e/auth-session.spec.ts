import { test, expect, type Page } from '@playwright/test'

const EMAIL = 'owner@demo.com'
const PASSWORD = 'demo1234'

async function login(page: Page, next?: string) {
  await page.goto(next ? `/login?next=${encodeURIComponent(next)}` : '/login')
  await page.locator('#email').fill(EMAIL)
  await page.locator('#password').fill(PASSWORD)
  await page.locator('form').getByRole('button').click()
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 })
}

test('reload and a new tab keep the session on /reports', async ({ page, context }) => {
  await login(page)
  await page.goto('/reports')
  await expect(page).toHaveURL(/\/reports/)
  await expect(page.getByRole('heading', { name: /^(דוחות|Reports)$/ })).toBeVisible()

  await page.reload()
  await expect(page).toHaveURL(/\/reports/)
  await expect(page.getByRole('heading', { name: /^(דוחות|Reports)$/ })).toBeVisible()

  const tab = await context.newPage()
  await tab.goto('/reports')
  await expect(tab).toHaveURL(/\/reports/)
  await expect(tab.getByRole('heading', { name: /^(דוחות|Reports)$/ })).toBeVisible()
  await tab.close()
})

test('logged-out deep link to /staff returns there after login', async ({ page }) => {
  await page.goto('/staff')
  await expect(page).toHaveURL(/\/login/)
  expect(new URL(page.url()).searchParams.get('next')).toBe('/staff')

  await page.locator('#email').fill(EMAIL)
  await page.locator('#password').fill(PASSWORD)
  await page.locator('form').getByRole('button').click()

  await expect(page).toHaveURL(/\/staff/)
  await expect(page.getByRole('heading', { name: /^(צוות|Staff)$/ })).toBeVisible()
})
