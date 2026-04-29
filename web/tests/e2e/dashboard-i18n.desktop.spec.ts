import { expect, test } from '@playwright/test'

import { login, uniqueLocalBaseUrl, uniqueSuffix, waitForUiReady } from './helpers'

test('首页最近异常在中文环境下翻译后端英文错误信息', async ({ page }) => {
  await login(page)

  const suffix = uniqueSuffix('i18n-dashboard')
  const baseUrl = uniqueLocalBaseUrl('i18n-dashboard')
  const setup = await page.evaluate(async ({ suffix, baseUrl }) => {
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `i18n-dashboard-site-${suffix}`,
        base_url: baseUrl,
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
  }, { suffix, baseUrl })

  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)

  await page.context().addCookies([
    {
      name: 'app-locale',
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
  await expect(page.getByTestId('daily-ops-failed-metric')).toContainText('1')
  await expect(page.getByTestId('daily-ops-failed-metric')).toHaveClass(/daily-ops-hero__metric--alert/)
})

test('首页核心区块提供明确的后续处理入口', async ({ page }) => {
  await login(page)
  await page.goto('/dashboard')
  await waitForUiReady(page)

  await expect(page.getByRole('link', { name: /接入站点账号|Onboard Sites and Accounts/ })).toHaveAttribute('href', '/setup')
  await expect(page.getByRole('link', { name: /查看今日任务|View Today Tasks/ })).toHaveAttribute('href', '/today')
  await expect(page.getByRole('link', { name: /处理异常/ }).first()).toHaveAttribute('href', '/incidents')
  await expect(page.getByRole('link', { name: /复核今日任务|Review Today Tasks/ })).toHaveAttribute('href', '/today')
})

test('首页任务工作台在英文环境下不回退中文文案', async ({ page }) => {
  await login(page)
  const suffix = uniqueSuffix('provider-i18n')
  const baseUrl = uniqueLocalBaseUrl('provider-i18n')
  const setup = await page.evaluate(async ({ suffix, baseUrl }) => {
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `provider-i18n-site-${suffix}`,
        base_url: baseUrl,
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
        display_name: `provider-i18n-user-${suffix}`,
        username: `provider-i18n-user-${suffix}`,
        auth_mode: 'linuxdo_oauth',
        password: 'provider-i18n-password',
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
        last_error_message: '未找到站点对应的 provider 配置',
      }),
    })

    return {
      siteStatus: siteResponse.status,
      accountStatus: accountResponse.status,
    }
  }, { suffix, baseUrl })
  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)
  await page.context().addCookies([
    {
      name: 'app-locale',
      value: 'en-US',
      domain: '127.0.0.1',
      path: '/',
      httpOnly: false,
      secure: false,
    },
  ])

  await page.goto('/dashboard')
  await waitForUiReady(page)

  const workbench = page.getByTestId('daily-task-workbench')
  await expect(workbench).toContainText('Task Inbox')
  await expect(workbench).toContainText('Review today account tasks by processing order')
  await expect(workbench).toContainText('Handle Incidents First')
  await expect(page.getByTestId('daily-ops-refresh-action')).toContainText('Refresh')
  await expect(workbench).toContainText('Provider configuration was not found for this site')
  await expect(workbench).not.toContainText('任务收件箱')
  await expect(workbench).not.toContainText('先处理异常')
  await expect(workbench).not.toContainText('未找到站点对应的 provider 配置')
})
