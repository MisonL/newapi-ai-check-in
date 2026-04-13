import { expect, test } from '@playwright/test'

import { login } from './helpers'

test('任务中心代理接口返回正确状态码', async ({ page }) => {
  await login(page)

  const responses = await page.evaluate(async () => {
    const paths = [
      '/api/ui/task-center/today',
      '/api/ui/task-center/incidents',
      '/api/ui/task-center/reports',
    ]
    return Promise.all(paths.map(async (path) => {
      const response = await fetch(path)
      return { path, status: response.status }
    }))
  })

  for (const response of responses) {
    expect(response.status, response.path).toBe(200)
  }
})

test('站点写入校验失败时保留真实 422 响应', async ({ page }) => {
  await login(page)

  const response = await page.evaluate(async () => {
    const request = await fetch('/api/ui/sites', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({}),
    })
    return {
      status: request.status,
      body: await request.text(),
    }
  })

  expect(response.status).toBe(422)
  expect(response.body).toContain('Field required')
})
