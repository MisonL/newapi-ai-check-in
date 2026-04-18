import { expect, test } from '@playwright/test'

import { login, waitForUiReady } from './helpers'

test('桌面端 Shell 密度收紧到工作台目标区间', async ({ page }) => {
  await login(page)
  await page.goto('/today')
  await waitForUiReady(page)

  const metrics = await page.evaluate(() => {
    const sidebar = document.querySelector('.page-shell__sidebar') as HTMLElement | null
    const topbar = document.querySelector('.topbar') as HTMLElement | null
    const pageHeader = document.querySelector('.page-header') as HTMLElement | null
    const summaryStrip = document.querySelector('.page-summary-strip') as HTMLElement | null

    return {
      sidebarWidth: sidebar?.getBoundingClientRect().width ?? 0,
      topbarHeight: topbar?.getBoundingClientRect().height ?? 0,
      pageHeaderPaddingTop: pageHeader ? Number.parseFloat(getComputedStyle(pageHeader).paddingTop) : 0,
      summaryStripPaddingTop: summaryStrip ? Number.parseFloat(getComputedStyle(summaryStrip).paddingTop) : 0,
    }
  })

  expect(metrics.sidebarWidth).toBeLessThanOrEqual(252)
  expect(metrics.topbarHeight).toBeLessThanOrEqual(72)
  expect(metrics.pageHeaderPaddingTop).toBeLessThanOrEqual(22)
  expect(metrics.summaryStripPaddingTop).toBeLessThanOrEqual(8)
})
