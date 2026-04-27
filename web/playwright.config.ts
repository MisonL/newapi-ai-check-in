import { defineConfig, devices } from '@playwright/test'

const useExternalServer = process.env.PLAYWRIGHT_EXTERNAL_SERVER === '1'
const controlPlanePort = process.env.PLAYWRIGHT_CONTROL_PLANE_PORT || '39381'
const webPort = process.env.PLAYWRIGHT_WEB_PORT || '39329'
const controlPlaneStartupTimeoutMs = 60_000
const webStartupTimeoutMs = 300_000
const controlPlaneUrl = `http://127.0.0.1:${controlPlanePort}`
const webUrl = `http://127.0.0.1:${webPort}`

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: webUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: {
        browserName: 'chromium',
        ...devices['Desktop Chrome'],
      },
      testMatch: /.*\.desktop\.spec\.ts/,
    },
    {
      name: 'mobile',
      use: {
        browserName: 'chromium',
        ...devices['iPhone 13'],
      },
      testMatch: /.*\.mobile\.spec\.ts/,
    },
  ],
  webServer: useExternalServer ? undefined : [
    {
      cwd: '..',
      command: `env CONTROL_PLANE_PORT=${controlPlanePort} CONTROL_PLANE_STORAGE_MODE=memory CONTROL_PLANE_BROWSER_ENABLED=false CONTROL_PLANE_SESSION_SECRET=test-session-secret CONTROL_PLANE_INTERNAL_TOKEN=test-internal-token CONTROL_PLANE_ADMIN_PASSWORD=test-admin-password .venv/bin/python control_plane_main.py`,
      url: `${controlPlaneUrl}/health`,
      reuseExistingServer: false,
      timeout: controlPlaneStartupTimeoutMs,
    },
    {
      cwd: '.',
      command: `env NUXT_CONTROL_PLANE_URL=${controlPlaneUrl} NUXT_CONTROL_PLANE_TOKEN=test-internal-token NUXT_SESSION_SECRET=test-session-secret npm run build && env NUXT_CONTROL_PLANE_URL=${controlPlaneUrl} NUXT_CONTROL_PLANE_TOKEN=test-internal-token NUXT_SESSION_SECRET=test-session-secret NUXT_PORT=${webPort} npm run start`,
      url: `${webUrl}/login`,
      reuseExistingServer: false,
      timeout: webStartupTimeoutMs,
    },
  ],
})
