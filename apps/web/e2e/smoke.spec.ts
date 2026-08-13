import { test, expect } from '@playwright/test'

test('health endpoint returns ok', async ({ request }) => {
  const response = await request.get('http://localhost:8080/api/v1/health')
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.status).toBe('ok')
})

test('homepage redirects to login', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/(login|auth)/)
})

test('login page renders form', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible()
  await expect(page.getByRole('textbox', { name: /password/i })).toBeVisible()
  await expect(page.getByRole('button', { name: /sign in|log in/i })).toBeVisible()
})

test('customer display page renders without auth', async ({ page }) => {
  // Should render without redirecting to login (public route)
  await page.goto('/display/test-location-id')
  // Should show "No active orders" or an order grid, never redirected to login
  await expect(page).not.toHaveURL(/\/(login|auth)/)
})
