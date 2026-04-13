import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('语言切换与调度下拉键盘交互正常', async ({ page }) => {
  await login(page)

  await page.getByRole('button', { name: /语言切换 中文|Language Switch/ }).click()
  await page.getByRole('option', { name: /英文|English/ }).click()
  await expect(page.getByRole('heading', { name: 'Home' })).toBeVisible()

  await page.goto('/schedules')
  await waitForUiReady(page)
  const enabledSelect = page.locator('#schedule-main_checkin-enabled')
  await enabledSelect.focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: 'Disabled' })).toBeFocused()
  await page.keyboard.press('ArrowUp')
  await expect(page.getByRole('option', { name: 'Enabled' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(enabledSelect).toBeFocused()
})

test('系统设置页下拉框支持键盘切换并保留焦点回收', async ({ page }) => {
  await login(page)

  await page.goto('/settings')
  await waitForUiReady(page)
  const strategySelect = page.locator('#settings-browser-strategy')
  await strategySelect.focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: /传统浏览器|Legacy/ })).toBeFocused()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: /仅 HTTP|HTTP-only/ })).toBeFocused()
  await page.keyboard.press('Home')
  await expect(page.getByRole('option', { name: /传统浏览器|Legacy/ })).toBeFocused()
  await page.keyboard.press('End')
  await expect(page.getByRole('option', { name: /仅 HTTP|HTTP-only/ })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(strategySelect).toBeFocused()
  await expect(strategySelect).toContainText(/仅 HTTP|HTTP-only/)
})
