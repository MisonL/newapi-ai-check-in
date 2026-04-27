import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('首页最近异常在中文环境下翻译后端英文错误信息', async ({ page }) => {
  await login(page)

  const setup = await page.evaluate(async () => {
    const suffix = `${Date.now()}-${Math.floor(Math.random() * 1000)}`
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `i18n-dashboard-site-${suffix}`,
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
        display_name: `i18n-dashboard-user-${suffix}`,
        username: `i18n-dashboard-user-${suffix}`,
        auth_mode: 'password',
        password: 'i18n-dashboard-password',
        api_user: '',
        session_cookies: {},
        enabled: true,
        session_status: 'unknown',
        last_checkin_status: 'failed',
        last_checkin_date: null,
        last_checkin_at: new Date().toISOString(),
        last_quota_awarded: 0,
        total_checkins: 0,
        total_quota_awarded: 0,
        last_error_message: 'Username or password is incorrect, or user has been banned',
      }),
    })

    return {
      siteStatus: siteResponse.status,
      accountStatus: accountResponse.status,
    }
  })

  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)

  await page.context().addCookies([
    {
      name: 'app_locale',
      value: 'zh-CN',
      domain: '127.0.0.1',
      path: '/',
      httpOnly: false,
      secure: false,
    },
  ])

  await page.goto('/dashboard')
  await waitForUiReady(page)

  await expect(page.getByText('用户名或密码错误，或账号已被封禁').first()).toBeVisible()
  await expect(page.getByText('Username or password is incorrect, or user has been banned')).toHaveCount(0)
})
