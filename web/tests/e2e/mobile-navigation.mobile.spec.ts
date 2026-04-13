import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('移动端页面导航可切换到历史与报表', async ({ page }) => {
  await login(page)
  await waitForUiReady(page)

  await page.getByRole('button', { name: /页面导航 首页|Page Navigation Home/ }).click()
  await page.getByRole('option', { name: /历史与报表|History and Reports/ }).click()
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

  await page.goto('/accounts')
  await waitForUiReady(page)
  await expect(page.locator('#account-site')).toBeDisabled()
  await expect(page.getByRole('button', { name: /Create Account|创建账号/ })).toBeDisabled()
  await expect(page.getByRole('link', { name: /Open Sites|前往站点/ }).first()).toBeVisible()
})
