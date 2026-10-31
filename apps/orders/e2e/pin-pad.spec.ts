import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'

const API = process.env.API_BASE_URL ?? 'http://localhost:8080/api/v1'

async function demoLocationId(request: APIRequestContext): Promise<string> {
  const login = await request.post(`${API}/auth/login`, {
    data: { email: 'owner@demo.com', password: 'demo1234' },
  })
  expect(login.ok()).toBeTruthy()
  const tokens = await login.json()
  const me = await request.get(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${tokens.accessToken}` },
  })
  expect(me.ok()).toBeTruthy()
  const user = await me.json()
  const locations = await request.get(`${API}/businesses/${user.businessId}/locations`, {
    headers: { Authorization: `Bearer ${tokens.accessToken}` },
  })
  expect(locations.ok()).toBeTruthy()
  const list = await locations.json()
  return list[0].id as string
}

async function configureDevice(page: Page, request: APIRequestContext, locationId: string) {
  const login = await request.post(`${API}/auth/login`, {
    data: { email: 'owner@demo.com', password: 'demo1234' },
  })
  expect(login.ok()).toBeTruthy()
  const tokens = await login.json()
  const registered = await request.post(`${API}/locations/${locationId}/devices`, {
    headers: { Authorization: `Bearer ${tokens.accessToken}` },
    data: { name: 'E2E PIN pad', type: 'pos' },
  })
  expect(registered.ok()).toBeTruthy()
  const device = await registered.json()
  await page.addInitScript(
    ({ locationId: id, deviceToken }) => {
      localStorage.setItem(
        'smartserve-device',
        JSON.stringify({
          state: { locationId: id, deviceToken, deviceType: 'pos', deviceName: 'E2E PIN pad' },
          version: 0,
        }),
      )
    },
    { locationId, deviceToken: device.token as string },
  )
}

async function openPinPad(page: Page, request: APIRequestContext) {
  const locationId = await demoLocationId(request)
  await configureDevice(page, request, locationId)
  await page.goto('/login')
  await page.getByRole('button', { name: /Demo Waiter/i }).click()
  await expect(page.getByTestId('pin-pad')).toBeVisible()
}

function assertLeftToRight(
  left: { x: number } | null,
  middle: { x: number } | null,
  right: { x: number } | null,
) {
  expect(left).not.toBeNull()
  expect(middle).not.toBeNull()
  expect(right).not.toBeNull()
  if (!left || !middle || !right) return
  expect(left.x).toBeLessThan(middle.x)
  expect(middle.x).toBeLessThan(right.x)
}

test('PIN keypad stays 1-2-3 under Hebrew RTL', async ({ page, request }) => {
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await openPinPad(page, request)

  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  const pad = page.getByTestId('pin-pad')
  await expect(pad).toHaveAttribute('dir', 'ltr')

  const one = await pad.getByRole('button', { name: '1', exact: true }).boundingBox()
  const two = await pad.getByRole('button', { name: '2', exact: true }).boundingBox()
  const three = await pad.getByRole('button', { name: '3', exact: true }).boundingBox()
  assertLeftToRight(one, two, three)

  const back = await pad.getByTestId('pin-pad-back').boundingBox()
  const zero = await pad.getByRole('button', { name: '0', exact: true }).boundingBox()
  const del = await pad.getByTestId('pin-pad-delete').boundingBox()
  assertLeftToRight(back, zero, del)

  await expectNoSeriousAxeViolations(page)

  await page.setViewportSize({ width: 1180, height: 820 })
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('PIN keypad stays usable on a phone viewport', async ({ page, request }) => {
  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  await openPinPad(page, request)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByTestId('pin-pad')).toBeVisible()
  const one = await page.getByRole('button', { name: '1', exact: true }).boundingBox()
  expect(one).not.toBeNull()
  if (!one) return
  expect(one.height).toBeGreaterThanOrEqual(48)
  await test.info().attach('after-en-dark-phone', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
