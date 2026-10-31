import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

const API = process.env.API_BASE_URL ?? 'http://localhost:8080/api/v1'
const WAITER_PIN = '1234'

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
    data: { name: 'E2E POS', type: 'pos' },
  })
  expect(registered.ok()).toBeTruthy()
  const device = await registered.json()
  await page.addInitScript(
    ({ locationId: id, deviceToken }) => {
      localStorage.setItem(
        'smartserve-device',
        JSON.stringify({
          state: { locationId: id, deviceToken, deviceType: 'pos', deviceName: 'E2E POS' },
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
}

test('reload and a new tab keep the session on /kitchen', async ({ page, context, request }) => {
  const locationId = await demoLocationId(request)
  await configureDevice(page, request, locationId)
  await pinLoginWaiter(page)
  await expect(page).toHaveURL(/\/orders/)

  await page.goto('/kitchen')
  await expect(page.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()

  await page.reload()
  await expect(page).toHaveURL(/\/kitchen/)
  await expect(page.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()

  const tab = await context.newPage()
  await tab.goto('/kitchen')
  await expect(tab).toHaveURL(/\/kitchen/)
  await expect(tab.getByRole('heading', { name: /תצוגת מטבח|Kitchen/i })).toBeVisible()
  await tab.close()
})

test('PIN session survives reload and logout returns to login', async ({ page, request }) => {
  const locationId = await demoLocationId(request)
  await configureDevice(page, request, locationId)
  await pinLoginWaiter(page)
  await expect(page).toHaveURL(/\/orders/)

  await page.reload()
  await expect(page).toHaveURL(/\/orders/)

  await page.getByRole('button', { name: /יציאה|התנתק|Log out|Logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
  await expect(page.getByRole('button', { name: /Demo Waiter/i })).toBeVisible()
})
