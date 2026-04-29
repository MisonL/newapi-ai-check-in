import { expect, type Page, test } from '@playwright/test'

import { login, uniqueLocalBaseUrl, uniqueSuffix, waitForUiReady } from './helpers'

async function createFailedDashboardTask(page: Page, prefix: string) {
  const suffix = uniqueSuffix(prefix)
  const baseUrl = uniqueLocalBaseUrl(prefix)
  const setup = await page.evaluate(async ({ suffix, baseUrl }) => {
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `${suffix}-site`,
        base_url: baseUrl,
        enabled: true,
        compatibility_level: 'standard',
        notes: '',
      }),
    })
    const site = await siteResponse.json()
    const accountResponse = await fetch('/api/ui/accounts', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        site_id: site.id,
        display_name: `${suffix}-user`,
        username: `${suffix}-user`,
        auth_mode: 'password',
        password: `${suffix}-password`,
        enabled: true,
      }),
    })
    await accountResponse.json()
    const generateResponse = await fetch('/api/ui/task-center/tasks/generate-today', { method: 'POST' })
    const executeResponse = await fetch('/api/ui/task-center/tasks/execute-today', { method: 'POST' })
    return {
      siteStatus: siteResponse.status,
      accountStatus: accountResponse.status,
      generateStatus: generateResponse.status,
      executeStatus: executeResponse.status,
    }
  }, { suffix, baseUrl })

  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)
  expect(setup.generateStatus).toBe(200)
  expect(setup.executeStatus).toBe(200)
}

test('首页摘要条优先展示任务生成状态', async ({ page }) => {
  await login(page)
  await page.goto('/dashboard')
  await waitForUiReady(page)

  const heroText = await page.locator('.daily-ops-hero').textContent()
  expect(heroText).toMatch(/今日状态|Today Status/)
  expect(heroText).toMatch(/今日额度|Quota Today/)
  await expect(page.getByTestId('daily-ops-primary-action')).toBeVisible()
})

test('首页日常运营台在桌面首屏保持紧凑层级', async ({ page }) => {
  await login(page)
  await page.goto('/dashboard')
  await waitForUiReady(page)

  const metrics = await page.evaluate(() => {
    const hero = document.querySelector('.daily-ops-hero') as HTMLElement | null
    const heroTitle = document.querySelector('.daily-ops-hero__copy h2') as HTMLElement | null
    const metricValue = document.querySelector('.daily-ops-hero__metrics strong') as HTMLElement | null
    const lowerGrid = document.querySelector('.daily-ops-grid') as HTMLElement | null

    return {
      heroHeight: hero?.getBoundingClientRect().height ?? 0,
      heroTitleFontSize: heroTitle ? Number.parseFloat(getComputedStyle(heroTitle).fontSize) : 0,
      metricValueFontSize: metricValue ? Number.parseFloat(getComputedStyle(metricValue).fontSize) : 0,
      lowerGridTop: lowerGrid?.getBoundingClientRect().top ?? 0,
      viewportHeight: window.innerHeight,
    }
  })

  expect(metrics.heroHeight).toBeGreaterThan(0)
  expect(metrics.lowerGridTop).toBeGreaterThan(0)
  expect(metrics.heroHeight).toBeLessThanOrEqual(260)
  expect(metrics.heroTitleFontSize).toBeLessThanOrEqual(32)
  expect(metrics.metricValueFontSize).toBeLessThanOrEqual(18)
  expect(metrics.lowerGridTop).toBeLessThan(metrics.viewportHeight * 0.78)
})

test('首页任务工作台按真实任务状态分组展示', async ({ page }) => {
  await login(page)
  await createFailedDashboardTask(page, 'dashboard-board')

  await page.goto('/dashboard')
  await waitForUiReady(page)

  await expect(page.getByTestId('daily-task-workbench')).toBeVisible()
  await expect(page.getByTestId('daily-task-lane-attention')).toBeVisible()
  await expect(page.getByTestId('daily-task-lane-active')).toBeVisible()
  await expect(page.getByTestId('daily-task-lane-done')).toBeVisible()
  await expect(page.getByTestId('daily-task-lane-attention').locator('.daily-task-card').first()).toBeVisible()
})

test('首页异常态强化并从异常卡片进入异常页', async ({ page }) => {
  await login(page)
  await createFailedDashboardTask(page, 'dashboard-alert')

  await page.goto('/dashboard')
  await waitForUiReady(page)

  await expect(page.getByTestId('daily-ops-failed-metric')).toHaveClass(/daily-ops-hero__metric--alert/)
  await expect(page.getByTestId('daily-ops-incident-action')).toBeVisible()
  await page.getByTestId('daily-task-lane-attention').locator('.daily-task-card').first().click()
  await expect(page).toHaveURL(/\/incidents$/)
})

test('首页不会把已禁用账号的旧异常当作待处理事项', async ({ page }) => {
  await login(page)
  await page.goto('/dashboard')
  await waitForUiReady(page)

  const readFailedMetricCount = async () => {
    const text = await page.getByTestId('daily-ops-failed-metric').textContent()
    return Number(text?.match(/\d+/)?.[0] || 0)
  }
  const baselineFailedCount = await readFailedMetricCount()

  const suffix = uniqueSuffix('dashboard-disabled')
  const baseUrl = uniqueLocalBaseUrl('dashboard-disabled')
  const setup = await page.evaluate(async ({ suffix, baseUrl }) => {
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `dashboard-disabled-site-${suffix}`,
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
        display_name: `disabled-alert-user-${suffix}`,
        username: `disabled-alert-user-${suffix}`,
        auth_mode: 'password',
        password: 'disabled-alert-password',
        api_user: '',
        session_cookies: {},
        enabled: false,
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
      displayName: `disabled-alert-user-${suffix}`,
    }
  }, { suffix, baseUrl })
  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)

  await page.goto('/dashboard')
  await waitForUiReady(page)

  expect(await readFailedMetricCount()).toBe(baselineFailedCount)
  await expect(page.getByText(setup.displayName)).toHaveCount(0)
})

test('今日任务页使用紧凑列表行承载任务', async ({ page }) => {
  await login(page)

  const suffix = uniqueSuffix('density')
  const baseUrl = uniqueLocalBaseUrl('density')
  const setup = await page.evaluate(async ({ suffix, baseUrl }) => {
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        name: `density-test-site-${suffix}`,
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
  }, { suffix, baseUrl })

  expect(setup.siteStatus).toBe(200)
  expect(setup.accountStatus).toBe(200)
  expect(setup.generateStatus).toBe(200)

  await page.goto('/today')
  await waitForUiReady(page)

  await expect(page.getByRole('heading', { name: /今日任务|Today/ })).toBeVisible()
  await expect(page.getByTestId('today-action-run-all')).toBeVisible()
  await expect(page.locator('.task-row').first()).toBeVisible()
})
