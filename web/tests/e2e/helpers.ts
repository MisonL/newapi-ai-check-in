import { expect, type Page } from '@playwright/test'

export const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD || 'test-admin-password'

export function uniqueSuffix(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}`
}

export function assertDefined<T>(value: T | null | undefined, name: string): T {
  if (value == null) {
    throw new Error(`${name} is null`)
  }
  return value
}

export async function waitForUiReady(page: Page) {
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(800)
}

export async function login(page: Page) {
  await page.goto('/login')
  const response = await page.evaluate(async (password) => {
    const request = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({ password }),
    })
    return {
      ok: request.ok,
      status: request.status,
    }
  }, adminPassword)
  expect(response.ok).toBeTruthy()
  await page.goto('/dashboard')
  await waitForUiReady(page)
  await expect(page).toHaveURL(/\/dashboard$/)
}

export async function selectAppOption(page: Page, triggerSelector: string, optionName: RegExp | string) {
  await page.locator(triggerSelector).click()
  await page.getByRole('option', { name: optionName }).click()
}

export async function revealPasswordField(page: Page, inputSelector: string) {
  const input = page.locator(inputSelector)
  await expect(input).toHaveAttribute('type', 'password')
  await input.locator('xpath=following-sibling::button').click()
  await expect(input).toHaveAttribute('type', 'text')
}

export async function createSiteViaApi(page: Page, overrides: Record<string, unknown> = {}) {
  const suffix = uniqueSuffix('api-site')
  const payload = {
    name: `E2E Site ${suffix}`,
    base_url: `http://127.0.0.1:${35000 + Math.floor(Math.random() * 1000)}`,
    enabled: true,
    compatibility_level: 'standard',
    notes: '',
    ...overrides,
  }
  const result = await page.evaluate(async (sitePayload) => {
    const response = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(sitePayload),
    })
    return {
      status: response.status,
      body: await response.json(),
    }
  }, payload)
  expect(result.status).toBe(200)
  return result.body as Record<string, any>
}

export async function createPasswordAccountViaApi(
  page: Page,
  siteId: string,
  overrides: Record<string, unknown> = {},
) {
  const suffix = uniqueSuffix('api-account')
  const payload = {
    site_id: siteId,
    display_name: `E2E Account ${suffix}`,
    username: `e2e-user-${suffix}`,
    auth_mode: 'password',
    password: 'e2e-password',
    enabled: true,
    ...overrides,
  }
  const result = await page.evaluate(async (accountPayload) => {
    const response = await fetch('/api/ui/accounts', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(accountPayload),
    })
    return {
      status: response.status,
      body: await response.json(),
    }
  }, payload)
  expect(result.status).toBe(200)
  return result.body as Record<string, any>
}
