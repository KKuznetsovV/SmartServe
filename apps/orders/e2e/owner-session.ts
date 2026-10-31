import { expect, type APIRequestContext, type Page } from '@playwright/test'

const API = process.env.API_BASE_URL ?? 'http://localhost:8080/api/v1'

/** Owner `/login` is 10/minute for the whole stack job; reuse one token per worker. */
let ownerAccessToken: string | undefined
let cachedLocationId: string | undefined

export async function ownerToken(request: APIRequestContext): Promise<string> {
  if (ownerAccessToken) return ownerAccessToken
  const login = await request.post(`${API}/auth/login`, {
    data: { email: 'owner@demo.com', password: 'demo1234' },
  })
  expect(login.ok(), await login.text()).toBeTruthy()
  const tokens = await login.json()
  ownerAccessToken = tokens.accessToken as string
  return ownerAccessToken
}

export async function demoLocationId(request: APIRequestContext): Promise<string> {
  if (cachedLocationId) return cachedLocationId
  const token = await ownerToken(request)
  const me = await request.get(`${API}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(me.ok(), await me.text()).toBeTruthy()
  const user = await me.json()
  const locations = await request.get(`${API}/businesses/${user.businessId}/locations`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(locations.ok(), await locations.text()).toBeTruthy()
  const list = await locations.json()
  cachedLocationId = list[0].id as string
  return cachedLocationId
}

export async function registerPosDevice(
  page: Page,
  request: APIRequestContext,
  locationId: string,
  name: string,
): Promise<void> {
  const token = await ownerToken(request)
  const registered = await request.post(`${API}/locations/${locationId}/devices`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, type: 'pos' },
  })
  expect(registered.ok(), await registered.text()).toBeTruthy()
  const device = await registered.json()
  await page.addInitScript(
    ({ locationId: id, deviceToken, deviceName }) => {
      localStorage.setItem(
        'smartserve-device',
        JSON.stringify({
          state: { locationId: id, deviceToken, deviceType: 'pos', deviceName },
          version: 0,
        }),
      )
    },
    { locationId, deviceToken: device.token as string, deviceName: name },
  )
}

export { API }
