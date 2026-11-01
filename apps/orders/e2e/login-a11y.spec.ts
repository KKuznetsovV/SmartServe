import { test, expect } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'
import { demoLocationId, registerPosDevice } from './owner-session'

test('orders staff picker has landmarks and no serious axe issues', async ({ page, request }) => {
  test.setTimeout(60_000)
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  const locationId = await demoLocationId(request)
  await registerPosDevice(page, request, locationId, 'E2E login a11y')
  await page.goto('/login')
  await expect(page.getByRole('main')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'SmartServe' })).toBeVisible()
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
