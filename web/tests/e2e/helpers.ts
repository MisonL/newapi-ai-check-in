import { expect, type Page } from '@playwright/test'

const adminPassword = 'test-admin-password'

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
