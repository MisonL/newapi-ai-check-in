import { expect, test } from '@playwright/test'

import { isE2ETestAccount, isE2ETestSite, uniqueLocalApiUrl, uniqueLocalBaseUrl, uniqueSuffix } from './helpers'

test('E2E helper uses deterministic unique local URLs without random ports', () => {
  const firstSuffix = uniqueSuffix('stable-url')
  const secondSuffix = uniqueSuffix('stable-url')
  expect(firstSuffix).not.toBe(secondSuffix)
  expect(firstSuffix).toMatch(/^stable-url-\d+-\d+$/)

  const firstBaseUrl = uniqueLocalBaseUrl('primary')
  const secondBaseUrl = uniqueLocalBaseUrl('primary')
  expect(firstBaseUrl).not.toBe(secondBaseUrl)
  expect(firstBaseUrl).toMatch(/^http:\/\/127\.0\.0\.1:9\/e2e-\d+-\d+-primary$/)
  expect(firstBaseUrl).not.toMatch(/:3[0]{3}(?:\/|$)/)

  const apiUrl = uniqueLocalApiUrl('primary')
  expect(apiUrl).toMatch(/^http:\/\/127\.0\.0\.1:9\/e2e-\d+-\d+-primary\/api\/user\/checkin$/)
})

test('E2E cleanup only targets deterministic fixture assets', () => {
  const fixtureSite = {
    id: 'site-fixture',
    name: 'E2E Site stable-url-123-1',
    base_url: uniqueLocalBaseUrl('cleanup'),
  }
  const realSite = {
    id: 'site-real',
    name: 'new-api-dev-3001',
    base_url: 'http://127.0.0.1:3001',
  }
  const realSiteWithGenericMarker = {
    id: 'site-assets-density-e2e-prod',
    name: 'assets density e2e-operations',
    base_url: 'http://127.0.0.1:39327',
  }

  expect(isE2ETestSite(fixtureSite)).toBe(true)
  expect(isE2ETestSite(realSite)).toBe(false)
  expect(isE2ETestSite(realSiteWithGenericMarker)).toBe(false)
  expect(isE2ETestAccount({ display_name: '真实用户', username: 'real-user', site_id: realSite.id }, new Set([fixtureSite.id]))).toBe(false)
  expect(isE2ETestAccount({ display_name: '任意名称', username: 'real-user', site_id: fixtureSite.id }, new Set([fixtureSite.id]))).toBe(true)
  expect(isE2ETestAccount({ display_name: 'i18n-dashboard-user-123', username: 'real-user', site_id: realSite.id }, new Set())).toBe(false)
  expect(isE2ETestAccount({ display_name: 'assets density e2e-user', username: 'real-user', site_id: realSite.id }, new Set())).toBe(false)
})
