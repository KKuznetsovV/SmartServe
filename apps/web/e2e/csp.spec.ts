import { test, expect } from '@playwright/test'

test('login page does not log CSP violations', async ({ page }) => {
  const cspErrors: string[] = []
  page.on('console', (msg) => {
    if (msg.type() === 'error' && /content security policy/i.test(msg.text())) {
      cspErrors.push(msg.text())
    }
  })
  await page.goto('/login')
  await expect(page.locator('form')).toBeVisible({ timeout: 15_000 })
  expect(cspErrors).toEqual([])
})
