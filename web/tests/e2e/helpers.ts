import { expect, type Page } from '@playwright/test'

export const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD || 'test-admin-password'

let uniqueCounter = 0
let localUrlCounter = 0

export function uniqueSuffix(prefix: string) {
  uniqueCounter += 1
  return `${prefix}-${process.pid}-${uniqueCounter}`
}

export function uniqueLocalBaseUrl(label = 'site') {
  localUrlCounter += 1
  const normalizedLabel = label.replace(/[^a-zA-Z0-9-]/g, '-').toLowerCase()
  return `http://127.0.0.1:9/e2e-${process.pid}-${localUrlCounter}-${normalizedLabel}`
}

export function uniqueLocalApiUrl(label = 'site') {
  return `${uniqueLocalBaseUrl(label)}/api/user/checkin`
}

const e2eBaseUrlPrefix = 'http://127.0.0.1:9/e2e-'

export function isE2ETestSite(site: Record<string, any>) {
  return String(site.base_url || '').startsWith(e2eBaseUrlPrefix)
}

export function isE2ETestAccount(account: Record<string, any>, testSiteIds: Set<string>) {
  return testSiteIds.has(String(account.site_id || ''))
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
    base_url: uniqueLocalBaseUrl(suffix),
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

export async function clearTaskCenterDataViaApi(page: Page) {
  const listed = await page.evaluate(async () => {
    const readJson = async (url: string) => {
      const response = await fetch(url)
      return {
        ok: response.ok,
        status: response.status,
        body: await response.json().catch(() => null),
      }
    }
    const sitesResponse = await readJson('/api/ui/sites')
    if (!sitesResponse.ok || !Array.isArray(sitesResponse.body)) {
      return { ok: false, stage: 'list_sites', status: sitesResponse.status }
    }
    const accountsResponse = await readJson('/api/ui/accounts')
    if (!accountsResponse.ok || !Array.isArray(accountsResponse.body)) {
      return { ok: false, stage: 'list_accounts', status: accountsResponse.status }
    }
    return {
      ok: true,
      sites: sitesResponse.body,
      accounts: accountsResponse.body,
    }
  })
  expect(listed, 'task center test data listing').toMatchObject({ ok: true })
  const sites = Array.isArray(listed.sites) ? listed.sites : []
  const accounts = Array.isArray(listed.accounts) ? listed.accounts : []
  const testSites = sites.filter((site: Record<string, any>) => isE2ETestSite(site))
  const testSiteIds = new Set(testSites.map((site: Record<string, any>) => String(site.id || '')))
  const testAccounts = accounts.filter((account: Record<string, any>) => isE2ETestAccount(account, testSiteIds))
  const result = await page.evaluate(async ({ accountIds, siteIds }) => {
    for (const accountId of accountIds) {
      const response = await fetch(`/api/ui/accounts/${accountId}`, { method: 'DELETE' })
      if (!response.ok && response.status !== 404) {
        return { ok: false, stage: 'delete_account', status: response.status, id: accountId }
      }
    }
    for (const siteId of siteIds) {
      const response = await fetch(`/api/ui/sites/${siteId}`, { method: 'DELETE' })
      if (!response.ok && response.status !== 404) {
        return { ok: false, stage: 'delete_site', status: response.status, id: siteId }
      }
    }
    return { ok: true }
  }, {
    accountIds: testAccounts.map((account: Record<string, any>) => String(account.id || '')),
    siteIds: testSites.map((site: Record<string, any>) => String(site.id || '')),
  })

  expect(result, 'task center test data cleanup').toMatchObject({ ok: true })
}
