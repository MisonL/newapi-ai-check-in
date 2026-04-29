import { expect, test } from '@playwright/test'

import {
  createPasswordAccountViaApi,
  createSiteViaApi,
  login,
  uniqueLocalBaseUrl,
  uniqueSuffix,
  waitForUiReady,
} from './helpers'

test('首页提供普通用户可理解的签到控制台闭环', async ({ page }) => {
  await login(page)

  await page.goto('/dashboard')
  await waitForUiReady(page)

  const consolePanel = page.getByTestId('dashboard-control-console')
  await expect(consolePanel).toBeVisible()
  await expect(consolePanel).toContainText(/接入状态/)
  await expect(consolePanel).toContainText(/今日任务/)
  await expect(consolePanel).toContainText(/执行结果/)
  await expect(consolePanel).toContainText(/异常闭环/)
  await expect(consolePanel.getByRole('link', { name: /配置站点账号/ })).toHaveAttribute('href', '/setup')
  await expect(consolePanel.getByRole('link', { name: /生成或执行任务/ })).toHaveAttribute('href', '/today')
  await expect(consolePanel.getByRole('link', { name: /处理失败账号/ })).toHaveAttribute('href', '/incidents')
})

test('接入页把 Provider 模板、站点、账号和任务生成串成向导', async ({ page }) => {
  await login(page)

  await page.goto('/setup')
  await waitForUiReady(page)

  const guide = page.getByTestId('setup-onboarding-guide')
  await expect(guide).toBeVisible()
  await expect(guide).toContainText(/Provider 模板/)
  await expect(guide).toContainText(/标准 NewAPI/)
  await expect(guide).toContainText(/NewAPI \+ WAF/)
  await expect(guide).toContainText(/保存后测试站点/)
  await expect(guide).toContainText(/保存后测试账号/)
  await expect(guide).toContainText(/生成今日任务/)
  await expect(guide.getByRole('link', { name: /去配置站点/ })).toHaveAttribute('href', '/sites')
  await expect(guide.getByRole('link', { name: /去配置账号/ })).toHaveAttribute('href', '/accounts')
})

test('站点页提供 new-api Provider 快速模板并能写入表单', async ({ page }) => {
  await login(page)

  await page.goto('/sites')
  await waitForUiReady(page)

  await page.getByTestId('site-provider-template-browser').click()
  await expect(page.locator('#site-compatibility')).toContainText(/浏览器回退/)
  await expect(page.locator('#site-notes')).toHaveValue(/WAF Cookie/)

  await page.getByTestId('site-provider-template-standard').click()
  await expect(page.locator('#site-compatibility')).toContainText(/标准兼容/)
  await expect(page.locator('#site-notes')).toHaveValue(/标准 NewAPI/)
})

test('异常页给失败账号提供诊断建议和修复入口', async ({ page }) => {
  await login(page)

  const suffix = uniqueSuffix('workflow-incident')
  const site = await createSiteViaApi(page, {
    name: `E2E Workflow Incident Site ${suffix}`,
    base_url: uniqueLocalBaseUrl('workflow-incident'),
  })
  await createPasswordAccountViaApi(page, String(site.id), {
    display_name: `E2E Workflow Incident Account ${suffix}`,
    username: `workflow-incident-${suffix}`,
    password: 'workflow-incident-password',
  })
  await page.evaluate(async () => {
    await fetch('/api/ui/task-center/tasks/generate-today', { method: 'POST' })
    await fetch('/api/ui/task-center/tasks/execute-today', { method: 'POST' })
  })

  await page.goto('/incidents')
  await waitForUiReady(page)

  const incident = page.locator('.incident-diagnosis-card').filter({ hasText: `E2E Workflow Incident Account ${suffix}` }).first()
  await expect(incident).toBeVisible()
  await expect(incident).toContainText(/建议处理/)
  await expect(incident).toContainText(/先测试账号/)
  await expect(incident.getByRole('link', { name: /打开账号详情/ })).toHaveAttribute('href', /\/accounts\?edit=/)
})

test('账号页和今日任务页提供面向用户的操作指引', async ({ page }) => {
  await login(page)

  const site = await createSiteViaApi(page, {
    name: `E2E Workflow Guide Site ${uniqueSuffix('workflow-guide')}`,
    base_url: uniqueLocalBaseUrl('workflow-guide'),
  })
  await createPasswordAccountViaApi(page, String(site.id), {
    display_name: 'E2E Workflow Guide Account',
    username: 'workflow-guide-user',
    password: 'workflow-guide-password',
  })
  await page.evaluate(async () => {
    await fetch('/api/ui/task-center/tasks/generate-today', { method: 'POST' })
  })

  await page.goto('/accounts')
  await waitForUiReady(page)
  const accountGuide = page.getByTestId('account-diagnosis-guide')
  await expect(accountGuide).toBeVisible()
  await expect(accountGuide).toContainText(/先测试账号/)
  await expect(accountGuide).toContainText(/失败后编辑或禁用/)

  await page.goto('/today')
  await waitForUiReady(page)
  const stageRail = page.getByTestId('today-stage-rail')
  await expect(stageRail).toBeVisible()
  await expect(stageRail).toContainText(/待执行/)
  await expect(stageRail).toContainText(/失败或阻塞/)
  await stageRail.getByRole('button', { name: /待执行/ }).click()
  await expect(page.locator('#today-action-status')).toContainText(/已聚焦待执行任务/)
})
