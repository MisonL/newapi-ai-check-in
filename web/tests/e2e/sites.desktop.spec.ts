import { expect, test } from '@playwright/test'

import { login, uniqueSuffix, waitForUiReady } from './helpers'

test('站点页会将完整 API 链接归一化为站点根地址', async ({ page }) => {
  await login(page)
  await page.goto('/sites')
  await waitForUiReady(page)

  const suffix = uniqueSuffix('site-normalize')
  const inputUrl = `https://example-${suffix}.com/api/user/checkin?month=2026-04`
  const normalizedUrl = `https://example-${suffix}.com`

  await page.locator('#site-name').fill('Primary Site')
  await page.locator('#site-url').fill(inputUrl)
  await page.getByRole('button', { name: /创建站点|Create Site/ }).click()

  await expect(page.getByText(normalizedUrl, { exact: true })).toBeVisible()
})
