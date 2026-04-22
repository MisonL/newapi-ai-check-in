import { expect, test } from '@playwright/test'

test('移动端登录页保持单卡控制台结构', async ({ page }) => {
  await page.goto('/login')
  await page.waitForLoadState('networkidle')

  const loginConsole = page.locator('.login-console')
  await expect(loginConsole).toHaveCount(1)
  await expect(page.locator('.login-shell__intro')).toHaveCount(0)
  await expect(page.locator('.login-console__topbar')).toHaveCount(1)

  const boundingBox = await loginConsole.boundingBox()
  expect(boundingBox).not.toBeNull()
  if (!boundingBox) {
    throw new Error('login-console boundingBox is null')
  }

  const viewport = page.viewportSize()
  expect(viewport).not.toBeNull()
  if (!viewport) {
    throw new Error('viewport size is null')
  }

  expect(boundingBox.width).toBeLessThanOrEqual(viewport.width - 20)
})
