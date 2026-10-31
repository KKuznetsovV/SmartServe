import { test, expect } from '@playwright/test'

test('customer display without a paired device goes to setup', async ({ page }) => {
  await page.goto('/display')
  await expect(page).toHaveURL(/setup/)
})
