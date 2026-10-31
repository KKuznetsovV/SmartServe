import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { expectNoSeriousAxeViolations } from './a11y'

const API = process.env.API_BASE_URL ?? 'http://localhost:8080/api/v1'
const WAITER_PIN = '1234'

let ownerAccessToken: string | undefined
let cachedLocationId: string | undefined

async function ownerToken(request: APIRequestContext): Promise<string> {
  if (ownerAccessToken) return ownerAccessToken
  const login = await request.post(`${API}/auth/login`, {
    data: { email: 'owner@demo.com', password: 'demo1234' },
  })
  expect(login.ok(), await login.text()).toBeTruthy()
  const tokens = await login.json()
  ownerAccessToken = tokens.accessToken as string
  return ownerAccessToken
}

async function demoLocationId(request: APIRequestContext): Promise<string> {
  if (cachedLocationId) return cachedLocationId
  const token = await ownerToken(request)
  const me = await request.get(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(me.ok()).toBeTruthy()
  const user = await me.json()
  const locations = await request.get(`${API}/businesses/${user.businessId}/locations`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(locations.ok()).toBeTruthy()
  const list = await locations.json()
  cachedLocationId = list[0].id as string
  return cachedLocationId
}

async function configureDevice(page: Page, request: APIRequestContext, locationId: string) {
  const token = await ownerToken(request)
  const registered = await request.post(`${API}/locations/${locationId}/devices`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: 'E2E order screen', type: 'pos' },
  })
  expect(registered.ok(), await registered.text()).toBeTruthy()
  const device = await registered.json()
  await page.addInitScript(
    ({ locationId: id, deviceToken }) => {
      localStorage.setItem(
        'smartserve-device',
        JSON.stringify({
          state: { locationId: id, deviceToken, deviceType: 'pos', deviceName: 'E2E order screen' },
          version: 0,
        }),
      )
    },
    { locationId, deviceToken: device.token as string },
  )
}

async function pinLoginWaiter(page: Page) {
  await page.goto('/login')
  await page.getByRole('button', { name: /Demo Waiter/i }).click()
  for (const digit of WAITER_PIN) {
    await page.getByRole('button', { name: digit, exact: true }).click()
  }
  await expect(page).toHaveURL(/\/orders/)
}

async function openTakeawayOrder(page: Page, request: APIRequestContext) {
  const locationId = await demoLocationId(request)
  await configureDevice(page, request, locationId)
  const token = await ownerToken(request)
  const created = await request.post(`${API}/orders`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { locationId, channel: 'takeaway' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const order = await created.json()
  await pinLoginWaiter(page)
  await page.goto(`/orders/${order.id}`)
  await expect(page.getByRole('heading', { name: /הזמנה|Order/i })).toBeVisible()
  return order.id as string
}

test('order screen localizes tiles and keeps cancel in an overflow menu', async ({ page, request }) => {
  await page.context().addCookies([
    { name: 'locale', value: 'he', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'light', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 1180, height: 820 })
  await openTakeawayOrder(page, request)

  await expect(page.getByRole('button', { name: /שתייה|עיקריות|ראשונות/ })).toBeVisible()
  const drinks = page.getByRole('button', { name: 'שתייה' })
  if (await drinks.count()) await drinks.click()
  await expect(page.getByTestId('menu-tile').first()).toBeVisible()
  const tile = page.getByTestId('menu-tile').first()
  const box = await tile.boundingBox()
  expect(box).not.toBeNull()
  if (box) expect(box.height).toBeGreaterThanOrEqual(64)

  await tile.click()
  await expect(page.getByText(/לא נשלח/)).toBeVisible()

  await page.getByTestId('order-overflow').click()
  await page.getByRole('menuitem', { name: /בטל הזמנה/ }).click()
  await expect(page.getByTestId('confirm-cancel-order')).toBeVisible()

  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-he-light-tablet', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})

test('order screen stays usable on a phone in English dark mode', async ({ page, request }) => {
  await page.context().addCookies([
    { name: 'locale', value: 'en', path: '/', domain: 'localhost' },
    { name: 'theme', value: 'dark', path: '/', domain: 'localhost' },
  ])
  await page.setViewportSize({ width: 390, height: 844 })
  await openTakeawayOrder(page, request)
  await expect(page.getByTestId('menu-tile').first()).toBeVisible()
  const overflow = page.getByTestId('order-overflow')
  const box = await overflow.boundingBox()
  expect(box).not.toBeNull()
  if (box) {
    expect(box.height).toBeGreaterThanOrEqual(48)
    expect(box.width).toBeGreaterThanOrEqual(48)
  }
  await expectNoSeriousAxeViolations(page)
  await test.info().attach('after-en-dark-phone', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  })
})
