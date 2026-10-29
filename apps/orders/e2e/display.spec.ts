import { test, expect } from '@playwright/test'

test('customer display page renders without auth', async ({ page }) => {
  await page.goto('/display/test-location-id')
  await expect(page).not.toHaveURL(/\/(login|auth)/)
  await expect(page.getByText(/no active orders|אין הזמנות פעילות/i)).toBeVisible()
})
