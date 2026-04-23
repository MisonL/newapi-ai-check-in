import { expect, test } from '@playwright/test'

import { assertDefined } from './helpers'

test('移动端登录页保持单卡控制台结构', async ({ page }) => {
  await page.goto('/login')
  await page.waitForLoadState('networkidle')

  const loginConsole = page.locator('.login-console')
  await expect(loginConsole).toHaveCount(1)
  await expect(page.locator('.login-shell__intro')).toHaveCount(0)
  await expect(page.locator('.login-console__topbar')).toHaveCount(1)

  const boundingBox = assertDefined(await loginConsole.boundingBox(), 'login-console boundingBox')
  const viewport = assertDefined(page.viewportSize(), 'viewport size')

  expect(boundingBox.width).toBeLessThanOrEqual(viewport.width - 20)
})
