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
  await expect(page.locator('#email')).toBeVisible()
  await expect(page.locator('#password')).toBeVisible()
  await expect(page.locator('form').getByRole('button')).toBeVisible()
})
