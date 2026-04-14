import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('站点页会将完整 API 链接归一化为站点根地址', async ({ page }) => {
  await login(page)
  await page.goto('/sites')
  await waitForUiReady(page)

  await page.locator('#site-name').fill('Primary Site')
  await page.locator('#site-url').fill('https://example.com/api/user/checkin?month=2026-04')
  await page.getByRole('button', { name: /创建站点|Create Site/ }).click()

  await expect(page.getByText(/站点地址已归一化为 https:\/\/example\.com|URL normalized to https:\/\/example\.com/)).toBeVisible()
  await expect(page.getByText('https://example.com', { exact: true })).toBeVisible()
})
