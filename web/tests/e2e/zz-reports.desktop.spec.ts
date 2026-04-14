import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('报表页默认隐藏空白日期并支持导出 CSV', async ({ page }) => {
  await login(page)

  const setupResult = await page.evaluate(async () => {
    const siteResponse = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        name: 'Report Site',
        base_url: 'https://report.example.com',
        enabled: true,
      }),
    })
    const site = await siteResponse.json()

    const accountResponse = await fetch('/api/ui/accounts', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        site_id: site.id,
        display_name: 'Report Account',
        username: 'report-user',
        auth_mode: 'password',
        password: 'report-password',
        enabled: true,
      }),
    })

    const taskResponse = await fetch('/api/ui/task-center/tasks/generate-today', {
      method: 'POST',
    })

    return {
      siteStatus: siteResponse.status,
      accountStatus: accountResponse.status,
      taskStatus: taskResponse.status,
    }
  })
  expect(setupResult.siteStatus).toBe(200)
  expect(setupResult.accountStatus).toBe(200)
  expect(setupResult.taskStatus).toBe(200)

  await page.goto('/reports')
  await waitForUiReady(page)

  const trendBadge = page.getByText(/趋势日期 \d+|Trend days \d+/)
  await expect(trendBadge).toContainText('1')

  await page.locator('#reports-show-empty-days').click()
  await page.getByRole('option', { name: /显示空白日期|Show empty days/ }).click()
  await waitForUiReady(page)

  await expect(trendBadge).not.toContainText('1')

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /导出报表 CSV|Export Report CSV/ }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toContain('task-center-report-')
  expect(download.suggestedFilename()).toMatch(/\.csv$/)
})
