import { expect, type Page, test } from '@playwright/test'

import {
  createPasswordAccountViaApi,
  createSiteViaApi,
  adminPassword,
  login,
  revealPasswordField,
  selectAppOption,
  uniqueSuffix,
  waitForUiReady,
} from './helpers'

const expectVisibleEnabledButtonsHitTestable = async (page: Page) => {
  const buttons = page.locator('button:visible:not(:disabled)')
  const buttonCount = await buttons.count()
  const issues: string[] = []

  for (let index = 0; index < buttonCount; index += 1) {
    const button = buttons.nth(index)
    const label = ((await button.textContent()) || '(unnamed button)').replace(/\s+/g, ' ').trim()
    const type = await button.getAttribute('type')
    if (!type) {
      issues.push(`${label}: missing explicit button type`)
    }

    try {
      await button.click({ trial: true, timeout: 2000 })
    } catch (error: any) {
      issues.push(`${label}: ${String(error.message || error).split('\n')[0]}`)
    }
  }

  expect(issues, `${page.url()} has non-hit-testable enabled buttons`).toEqual([])
}

test('登录页、Shell 导航、主题切换和退出登录动作正常', async ({ page }) => {
  await page.goto('/login?next=/today')
  await waitForUiReady(page)

  const submitButton = page.getByRole('button', { name: /登录|Login/ })

  await submitButton.click()
  await expect(page.getByRole('alert')).toContainText(/密码不能为空|Password is required/)

  await page.locator('#password').fill('wrong-password')
  await revealPasswordField(page, '#password')
  await page.locator('#password').fill('wrong-password')
  await submitButton.click()
  await expect(page.getByRole('alert')).toContainText(/密码错误|Invalid password/)

  await page.locator('#password').fill(adminPassword)
  await submitButton.click()
  await expect(page).toHaveURL(/\/today$/)
  await expect(page.getByRole('heading', { name: /今日任务|Today/ })).toBeVisible()

  await page.locator('.global-topbar__nav').getByRole('link', { name: /站点|Sites/ }).click()
  await expect(page).toHaveURL(/\/sites$/)

  await page.getByRole('button', { name: /主题切换|Theme Switch/ }).click()
  await page.getByRole('option', { name: /暗色|Dark/ }).click()
  await expect.poll(() => page.evaluate(() => document.documentElement.classList.contains('dark'))).toBe(true)

  await page.getByRole('button', { name: /退出登录|Log out/ }).click()
  await expect(page).toHaveURL(/\/login$/)
})

test('主要刷新按钮均有明确点击反馈', async ({ page }) => {
  await login(page)

  await page.goto('/dashboard')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新首页|Refresh Home/ }).click()
  await expect(page.getByText(/首页已刷新|Home refreshed/)).toBeVisible()

  await page.goto('/today')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新今日任务|Refresh Today Tasks/ }).click()
  await expect(page.locator('#today-action-status')).toContainText(/今日任务已刷新|Today tasks refreshed/)
  await expect(page.getByTestId('today-action-refresh')).toHaveClass(/button--recent-action/)
  await expect(page.getByTestId('today-action-refresh-receipt')).toContainText(/已响应|Responded/)
  await expect(page.getByTestId('today-action-result')).toContainText(/刷新今日任务|Refresh Today Tasks/)
  await page.getByTestId('today-action-execute').click()
  await expect(page.locator('#today-action-status')).toContainText(/当前没有待执行任务|There are no pending tasks/)
  await expect(page.getByTestId('today-action-execute')).toHaveClass(/button--recent-action/)
  await expect(page.getByTestId('today-action-execute-receipt')).toContainText(/已响应|Responded/)
  await expect(page.getByTestId('today-action-result')).toContainText(/检查待处理任务|Check Pending Tasks/)
  await page.getByTestId('today-action-import').click()
  await expect(page.locator('#today-action-status')).toContainText(/旧配置中没有新增站点或账号|已导入站点|No new sites or accounts|Imported/)
  await expect(page.getByTestId('today-action-import')).toHaveClass(/button--recent-action/)
  await expect(page.getByTestId('today-action-import-receipt')).toContainText(/已响应|Responded/)
  await expect(page.getByTestId('today-action-result')).toContainText(/导入旧主签到配置|Import Legacy Primary Config/)
  await page.getByTestId('today-action-generate').click()
  await expect(page.locator('#today-action-status')).toContainText(/没有可生成任务的启用账号|已生成今日任务|今日任务已存在|No enabled accounts|Generated|already exist/)
  await expect(page.getByTestId('today-action-generate')).toHaveClass(/button--recent-action/)
  await expect(page.getByTestId('today-action-generate-receipt')).toContainText(/已响应|Responded/)
  await expect(page.getByTestId('today-action-result')).toContainText(/生成今日任务|Generate Today Tasks/)

  await page.goto('/sites')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新站点|Refresh Sites/ }).click()
  await expect(page.getByText(/站点已刷新|Sites refreshed/)).toBeVisible()

  await page.goto('/accounts')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新账号|Refresh Accounts/ }).click()
  await expect(page.getByText(/账号已刷新|Accounts refreshed/)).toBeVisible()

  await page.goto('/reports')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新报表|Refresh Reports/ }).click()
  await expect(page.getByText(/报表已刷新|Reports refreshed/)).toBeVisible()

  await page.goto('/incidents')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新异常|Refresh Incidents/ }).click()
  await expect(page.getByText(/异常已刷新|Incidents refreshed/)).toBeVisible()
})

test('核心页面可见启用按钮均无遮挡可命中', async ({ page }) => {
  await login(page)

  const routes = [
    '/dashboard',
    '/today',
    '/sites',
    '/accounts',
    '/reports',
    '/incidents',
    '/settings',
    '/main-checkin',
    '/schedules',
    '/aux-jobs',
  ]

  for (const route of routes) {
    await page.goto(route)
    await waitForUiReady(page)
    await expectVisibleEnabledButtonsHitTestable(page)
  }
})

test('站点与账号表单的创建、编辑、筛选和重置动作正常', async ({ page }) => {
  await login(page)

  const suffix = uniqueSuffix('assets')
  const siteName = `E2E UI Site ${suffix}`
  const sitePort = 39000 + Math.floor(Math.random() * 1000)
  const siteUrl = `http://127.0.0.1:${sitePort}/api/user/checkin`
  const normalizedSiteUrl = `http://127.0.0.1:${sitePort}`
  const passwordAccountName = `E2E Password ${suffix}`
  const cookieAccountName = `E2E Cookie ${suffix}`

  await page.goto('/sites')
  await waitForUiReady(page)
  await page.locator('#site-name').fill(siteName)
  await page.locator('#site-url').fill(siteUrl)
  await selectAppOption(page, '#site-compatibility', /浏览器回退|Browser/)
  await selectAppOption(page, '#site-enabled', /已禁用|Disabled/)
  await selectAppOption(page, '#site-enabled', /已启用|Enabled/)
  await page.locator('#site-notes').fill('site form smoke')
  await page.getByRole('button', { name: /创建站点|Create Site/ }).click()
  await expect(page.getByText(/站点已创建|Site created/)).toBeVisible()
  await expect(page.getByText(normalizedSiteUrl, { exact: true })).toBeVisible()

  const siteRow = page.locator('.asset-row').filter({ hasText: siteName }).first()
  await siteRow.getByRole('button', { name: /探测站点|Probe Site/ }).click()
  await expect(page.getByText(/站点探测完成|Site probe completed|站点不可达|Site unreachable/)).toBeVisible()
  await siteRow.getByRole('button', { name: /编辑|Edit/ }).click()
  await expect(page.getByText(new RegExp(`正在编辑站点 ${siteName}|Editing site ${siteName}`))).toBeVisible()
  await expect(page.locator('#site-name')).toBeFocused()
  await page.locator('#site-notes').fill('site form updated')
  await page.getByRole('button', { name: /保存站点修改|Save Site/ }).click()
  await expect(page.getByText(/站点已更新|Site updated/)).toBeVisible()
  await page.getByRole('button', { name: /清空表单|Clear Form/ }).click()
  await expect(page.locator('#site-name')).toHaveValue('')

  await page.goto('/accounts')
  await waitForUiReady(page)
  await selectAppOption(page, '#account-site', siteName)
  await page.locator('#account-display-name').fill(passwordAccountName)
  await page.locator('#account-username').fill(`password-${suffix}`)
  await page.locator('#account-password').fill('password-secret')
  await revealPasswordField(page, '#account-password')
  await page.locator('#account-password').fill('password-secret')
  await page.getByRole('button', { name: /创建账号|Create Account/ }).click()
  await expect(page.getByText(/账号已创建|Account created/)).toBeVisible()

  const passwordRow = page.locator('.asset-row').filter({ hasText: passwordAccountName }).first()
  await passwordRow.getByRole('button', { name: /测试账号|Test Account/ }).click()
  await expect(page.getByText(/账号预检完成|Account preflight completed|账号不可用|Account unavailable/)).toBeVisible()
  await passwordRow.getByRole('button', { name: /编辑|Edit/ }).click()
  await expect(page.getByText(new RegExp(`正在编辑账号 ${passwordAccountName}|Editing account ${passwordAccountName}`))).toBeVisible()
  await expect(page.locator('#account-display-name')).toBeFocused()
  await page.locator('#account-display-name').fill(`${passwordAccountName} Updated`)
  await page.getByRole('button', { name: /保存账号修改|Save Account/ }).click()
  await expect(page.getByText(/账号已更新|Account updated/)).toBeVisible()
  await page.getByRole('button', { name: /清空表单|Clear Form/ }).click()
  await expect(page.locator('#account-display-name')).toHaveValue('')

  await selectAppOption(page, '#account-auth-mode', /Cookie 会话|Cookie Session/)
  await selectAppOption(page, '#account-site', siteName)
  await page.locator('#account-display-name').fill(cookieAccountName)
  await page.locator('#account-api-user').fill(`cookie-${suffix}`)
  await page.locator('#account-cookies').fill('{bad-json')
  await page.getByRole('button', { name: /创建账号|Create Account/ }).click()
  await expect(page.getByText(/JSON 格式不正确|Invalid JSON/)).toBeVisible()

  await page.locator('#account-cookies').fill('{"session":"cookie-value"}')
  await page.getByRole('button', { name: /创建账号|Create Account/ }).click()
  await expect(page.getByText(/账号已创建|Account created/)).toBeVisible()

  await selectAppOption(page, '#account-site-filter', siteName)
  await selectAppOption(page, '#account-auth-filter', /Cookie 会话|Cookie Session/)
  await expect(page.getByText(cookieAccountName).first()).toBeVisible()
  await expect(page.getByText(`${passwordAccountName} Updated`).first()).toHaveCount(0)
})

test('站点与账号清单支持删除并同步级联结果', async ({ page }) => {
  await login(page)

  const suffix = uniqueSuffix('delete-assets')
  const site = await createSiteViaApi(page, {
    name: `E2E Delete Site ${suffix}`,
    base_url: `http://127.0.0.1:${37000 + Math.floor(Math.random() * 1000)}`,
  })
  const account = await createPasswordAccountViaApi(page, String(site.id), {
    display_name: `E2E Delete Account ${suffix}`,
    username: `delete-${suffix}`,
    password: 'delete-password',
  })

  await page.goto('/accounts')
  await waitForUiReady(page)
  const accountRow = page.locator('.asset-row').filter({ hasText: String(account.display_name) }).first()
  await accountRow.getByRole('button', { name: /删除账号|Delete Account/ }).click()
  await accountRow.getByRole('button', { name: /确认删除账号|Confirm Delete Account/ }).click()
  await expect(page.getByText(/账号已删除，已同步清理|Account deleted and related records cleaned/)).toBeVisible()
  await expect(page.locator('.asset-row').filter({ hasText: String(account.display_name) })).toHaveCount(0)

  await page.goto('/sites')
  await waitForUiReady(page)
  const siteRow = page.locator('.asset-row').filter({ hasText: String(site.name) }).first()
  await siteRow.getByRole('button', { name: /删除站点|Delete Site/ }).click()
  await siteRow.getByRole('button', { name: /确认删除站点|Confirm Delete Site/ }).click()
  await expect(page.getByText(/站点已删除，已同步清理|Site deleted and related records cleaned/)).toBeVisible()
  await expect(page.locator('.asset-row').filter({ hasText: String(site.name) })).toHaveCount(0)
})

test('今日任务、异常处理和报表筛选动作正常', async ({ page }) => {
  test.setTimeout(60000)
  await login(page)

  const suffix = uniqueSuffix('task-flow')
  const site = await createSiteViaApi(page, {
    name: `E2E Flow Site ${suffix}`,
    base_url: 'http://127.0.0.1:9',
  })
  const account = await createPasswordAccountViaApi(page, String(site.id), {
    display_name: `E2E Flow Account ${suffix}`,
    username: `flow-${suffix}`,
    password: 'flow-password',
  })

  await page.goto('/today')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /生成今日任务|Generate Today/ }).click()
  await expect(page.locator('#today-action-status')).toContainText(/已生成今日任务|Generated today/)

  await page.getByRole('button', { name: /执行账号任务|Run Account Task/ }).first().click()
  await expect(page.locator('#today-action-status')).toContainText(/账号任务执行失败|Account task failed|账号任务已阻塞|Account task blocked/, { timeout: 20000 })
  await expect(page.getByRole('button', { name: /重置后重试|Reset and Retry/ }).first()).toBeVisible()

  await page.getByRole('button', { name: /重置后重试|Reset and Retry/ }).first().click()
  await expect(page.locator('#today-action-status')).toContainText(/任务已重置为待执行|reset to pending/)
  await page.getByRole('button', { name: /执行待处理任务|Run Pending Tasks/ }).click()
  await expect(page.locator('#today-action-status')).toContainText(/已批量执行|Batch executed/, { timeout: 20000 })

  await selectAppOption(page, '#today-status-filter', /失败|failed/)
  await selectAppOption(page, '#today-site-filter', String(site.name))
  await selectAppOption(page, '#today-auth-filter', /密码登录|Password/)
  await selectAppOption(page, '#today-executor-filter', /标准接口|Standard/)
  await expect(page.getByText(String(account.display_name)).first()).toBeVisible()

  await page.goto('/incidents')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /刷新异常|Refresh Incidents/ }).click()
  await selectAppOption(page, '#incident-site-filter', String(site.name))
  await selectAppOption(page, '#incident-severity-filter', /high|高/)
  await expect(page.getByText(String(account.display_name)).first()).toBeVisible()
  const incidentCard = page.locator('.subcard').filter({ hasText: String(account.display_name) }).first()
  await incidentCard.getByRole('button', { name: /标记已解决|Mark Resolved/ }).click()
  await expect(page.getByText(/异常已标记为已解决|Incident marked resolved/)).toBeVisible()
  await expect(page.locator('.subcard').filter({ hasText: String(account.display_name) })).toHaveCount(0)

  await page.goto('/reports')
  await waitForUiReady(page)
  await page.locator('#reports-date-from').fill('2099-01-02')
  await page.locator('#reports-date-to').fill('2099-01-01')
  await page.getByRole('button', { name: /应用筛选|Apply Filters/ }).click()
  await expect(page.getByText(/开始日期不能晚于结束日期|Start date/)).toBeVisible()
})

test('今日任务页单账号动作完成后保留下一步按钮入口', async ({ page }) => {
  test.setTimeout(60000)
  await login(page)

  const suffix = uniqueSuffix('today-next-action')
  const site = await createSiteViaApi(page, {
    name: `E2E Next Action Site ${suffix}`,
    base_url: `http://127.0.0.1:${38000 + Math.floor(Math.random() * 1000)}`,
  })
  const account = await createPasswordAccountViaApi(page, String(site.id), {
    display_name: `E2E Next Action Account ${suffix}`,
    username: `next-action-${suffix}`,
    password: 'next-action-password',
  })

  await page.goto('/today')
  await waitForUiReady(page)
  await page.getByRole('button', { name: /生成今日任务|Generate Today/ }).click()

  const taskRow = page.locator('.task-row').filter({ hasText: String(account.display_name) }).first()
  await expect(taskRow.getByRole('button', { name: /执行账号任务|Run Account Task/ })).toBeVisible()
  await taskRow.getByRole('button', { name: /执行账号任务|Run Account Task/ }).click()
  await expect(page.getByText(/账号任务执行失败|Account task failed|账号任务已阻塞|Account task blocked/)).toBeVisible({ timeout: 20000 })

  const finalText = await taskRow.textContent()
  await selectAppOption(page, '#today-status-filter', /阻塞|blocked/i.test(finalText || '') ? /已阻塞|blocked/i : /失败|failed/i)
  const failedOrBlockedRow = page.locator('.task-row').filter({ hasText: String(account.display_name) }).first()
  await failedOrBlockedRow.getByRole('button', { name: /重置后重试|Reset and Retry/ }).click()
  await expect(page.getByText(/任务已重置为待执行|reset to pending/)).toBeVisible()

  const pendingRow = page.locator('.task-row').filter({ hasText: String(account.display_name) }).first()
  await expect(pendingRow.getByRole('button', { name: /执行账号任务|Run Account Task/ })).toBeVisible()
  await pendingRow.getByRole('button', { name: /执行账号任务|Run Account Task/ }).click()
  await expect(page.getByText(/账号任务执行失败|Account task failed|账号任务已阻塞|Account task blocked/)).toBeVisible({ timeout: 20000 })
  await expect(pendingRow.getByRole('button', { name: /重置后重试|Reset and Retry/ })).toBeVisible()
})

test('今日任务页执行类按钮有忙碌锁和结果反馈', async ({ page }) => {
  test.setTimeout(60000)
  await login(page)

  const suffix = uniqueSuffix('today-lock')
  const site = await createSiteViaApi(page, {
    name: `E2E Lock Site ${suffix}`,
    base_url: `http://127.0.0.1:${36000 + Math.floor(Math.random() * 1000)}`,
  })
  const account = await createPasswordAccountViaApi(page, String(site.id), {
    display_name: `E2E Lock Account ${suffix}`,
    username: `lock-${suffix}`,
    password: 'lock-password',
  })
  await page.evaluate(async () => {
    await fetch('/api/ui/task-center/tasks/generate-today', { method: 'POST' })
  })
  const taskId = await page.evaluate(async (accountId) => {
    const response = await fetch('/api/ui/task-center/today')
    const today = await response.json()
    return today.tasks.find((task: any) => task.account_id === accountId)?.id
  }, account.id)
  expect(taskId).toBeTruthy()

  await page.route(`**/api/ui/task-center/tasks/${taskId}/execute`, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500))
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: taskId,
        status: 'failed',
        error_message: 'simulated delayed failure',
      }),
    })
  })

  await page.goto('/today')
  await waitForUiReady(page)
  const taskRow = page.locator('.task-row').filter({ hasText: String(account.display_name) }).first()
  await taskRow.getByRole('button', { name: /执行账号任务|Run Account Task/ }).click()

  await expect(taskRow.getByRole('button', { name: /执行中|Running/ })).toBeDisabled()
  await expect(page.getByRole('button', { name: /生成今日任务|Generate Today/ })).toBeDisabled()
  await expect(page.getByRole('button', { name: /刷新今日任务|Refresh Today/ })).toBeDisabled()
  await expect(page.getByText(/账号任务执行失败：simulated delayed failure|Account task failed: simulated delayed failure/)).toBeVisible()
})
