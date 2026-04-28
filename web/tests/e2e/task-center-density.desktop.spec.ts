import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('首页摘要条优先展示任务生成状态', async ({ page }) => {
  await login(page)
  await page.goto('/dashboard')
  await waitForUiReady(page)

  const heroText = await page.locator('.daily-ops-hero').textContent()
  expect(heroText).toMatch(/今日状态|Today Status/)
  expect(heroText).toMatch(/今日额度|Quota Today/)
  await expect(page.getByTestId('daily-ops-primary-action')).toBeVisible()
})

test('今日任务页使用紧凑列表行承载任务', async ({ page }) => {
  await login(page)

  const setup = await page.evaluate(async () => {
    const suffix = `${Date.now()}-${Math.floor(Math.random() * 1000)}`
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `density-test-site-${suffix}`,
        base_url: `http://127.0.0.1:${3100 + Math.floor(Math.random() * 500)}`,
        enabled: true,
        compatibility_level: 'standard',
        last_probe_status: 'unknown',
        checkin_enabled_detected: null,
        checkin_min_quota_detected: null,
        checkin_max_quota_detected: null,
        notes: '',
      }),
    })
    const site = await siteResponse.json()
    const accountResponse = await fetch('/api/ui/accounts', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        site_id: site.id,
        display_name: `density-user-${suffix}`,
        username: `density-user-${suffix}`,
        auth_mode: 'password',
        password: 'density-password',
        api_user: '',
        session_cookies: {},
        enabled: true,
        session_status: 'unknown',
        last_checkin_status: 'pending',
        last_checkin_date: null,
        last_checkin_at: null,
        last_quota_awarded: 0,
        total_checkins: 0,
        total_quota_awarded: 0,
        last_error_message: '',
      }),
    })
    await accountResponse.json()
    const generateResponse = await fetch('/api/ui/task-center/tasks/generate-today', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
    })
    return {
      siteStatus: siteResponse.status,
      accountStatus: accountResponse.status,
      generateStatus: generateResponse.status,
    }
  })

  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)
  expect(setup.generateStatus).toBe(200)

  await page.goto('/today')
  await waitForUiReady(page)

  await expect(page.getByRole('heading', { name: /今日任务|Today/ })).toBeVisible()
  await expect(page.getByTestId('today-action-run-all')).toBeVisible()
  await expect(page.locator('.task-row').first()).toBeVisible()
})
