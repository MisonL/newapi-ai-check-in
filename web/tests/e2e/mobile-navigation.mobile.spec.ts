import { expect, test } from '@playwright/test'

import { createPasswordAccountViaApi, createSiteViaApi, login, uniqueLocalBaseUrl, uniqueSuffix, waitForUiReady } from './helpers'

test('移动端页面导航可切换到历史与报表', async ({ page }) => {
  await login(page)
  await waitForUiReady(page)

  await page.getByRole('button', { name: /页面导航 首页|Page Navigation Home/ }).click()
  await page.getByRole('option', { name: /^报表$|^Reports$/ }).click()
  await expect(page).toHaveURL(/\/reports$/)
  await expect(page.getByRole('heading', { name: /历史与报表|History and Reports/ })).toBeVisible()
})

test('移动端账号页认证方式切换后表单字段同步更新', async ({ page }) => {
  await login(page)

  await page.goto('/accounts')
  await waitForUiReady(page)
  await page.locator('#account-auth-mode').click()
  await page.getByRole('option', { name: /Cookie Session|Cookie 会话/ }).click()
  await expect(page.getByLabel(/API User|API 用户/)).toBeVisible()
  await expect(page.getByLabel(/Cookies JSON/)).toBeVisible()
  await expect(page.getByLabel(/Username|用户名/)).toHaveCount(0)
})

test('移动端账号空态显式禁用无站点创建路径', async ({ page }) => {
  await login(page)

  await page.route('**/api/ui/sites**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '[]',
    })
  })
  await page.route('**/api/ui/accounts**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '[]',
    })
  })

  await page.getByRole('button', { name: /页面导航 首页|Page Navigation Home/ }).click()
  await page.getByRole('option', { name: /^账号清单$|^Account List$/ }).click()
  await expect(page).toHaveURL(/\/accounts$/)
  await waitForUiReady(page)
  await expect(page.locator('#account-site')).toBeDisabled()
  await expect(page.getByRole('button', { name: /Create Account|创建账号/ })).toBeDisabled()
  await expect(page.getByRole('link', { name: /Open Sites|前往站点/ }).first()).toBeVisible()
})

test('移动端今日任务操作按钮使用完整触控热区', async ({ page }) => {
  await login(page)

  const suffix = uniqueSuffix('mobile-touch')
  const site = await createSiteViaApi(page, {
    name: `E2E Mobile Touch Site ${suffix}`,
    base_url: uniqueLocalBaseUrl('mobile-touch'),
  })
  const account = await createPasswordAccountViaApi(page, String(site.id), {
    display_name: `E2E Mobile Touch Account ${suffix}`,
    username: `mobile-touch-${suffix}`,
    password: 'mobile-touch-password',
  })
  await page.evaluate(async () => {
    await fetch('/api/ui/task-center/tasks/generate-today', { method: 'POST' })
  })

  await page.goto('/today')
  await waitForUiReady(page)
  const taskRow = page.locator('.task-row').filter({ hasText: String(account.display_name) }).first()
  const actionButton = taskRow.getByRole('button', { name: /执行账号任务|Run Account Task/ })
  await expect(actionButton).toBeVisible()

  const metrics = await actionButton.evaluate((button) => {
    const buttonBox = button.getBoundingClientRect()
    const rowBox = button.closest('.task-row')?.getBoundingClientRect()
    return {
      buttonHeight: buttonBox.height,
      buttonWidth: buttonBox.width,
      rowWidth: rowBox?.width || 0,
    }
  })

  expect(metrics.buttonHeight).toBeGreaterThanOrEqual(44)
  expect(metrics.buttonWidth).toBeGreaterThanOrEqual(metrics.rowWidth * 0.9)
})
