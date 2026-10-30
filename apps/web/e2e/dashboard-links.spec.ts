import { test, expect, type Page } from '@playwright/test'

const EMAIL = 'owner@demo.com'
const PASSWORD = 'demo1234'
const ORDERS_APP = (process.env.ORDERS_BASE_URL ?? 'http://localhost:3001').replace(/\/$/, '')

async function login(page: Page) {
  await page.goto('/login')
  await page.locator('#email').fill(EMAIL)
  await page.locator('#password').fill(PASSWORD)
  await page.locator('form').getByRole('button').click()
  await expect(page).not.toHaveURL(/\/login/, { timeout: 15_000 })
}

test('dashboard order and floor-plan links go to the orders app', async ({ page }) => {
  await login(page)
  await page.goto('/dashboard')

  await expect(page.getByRole('link', { name: /הזמנה חדשה|New Order/ })).toHaveAttribute(
    'href',
    `${ORDERS_APP}/orders`,
  )
  await expect(page.getByRole('link', { name: /תוכנית ישיבה|Floor Plan/ })).toHaveAttribute(
    'href',
    `${ORDERS_APP}/tables`,
  )
})
