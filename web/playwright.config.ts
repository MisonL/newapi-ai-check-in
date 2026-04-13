import { defineConfig, devices } from '@playwright/test'

const useExternalServer = process.env.PLAYWRIGHT_EXTERNAL_SERVER === '1'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:39329',
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
      command: 'env CONTROL_PLANE_PORT=18081 CONTROL_PLANE_BROWSER_ENABLED=false CONTROL_PLANE_SESSION_SECRET=test-session-secret CONTROL_PLANE_INTERNAL_TOKEN=test-internal-token CONTROL_PLANE_ADMIN_PASSWORD=test-admin-password .venv/bin/python control_plane_main.py',
      url: 'http://127.0.0.1:18081/health',
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      cwd: '.',
      command: 'env NUXT_CONTROL_PLANE_URL=http://127.0.0.1:18081 NUXT_CONTROL_PLANE_TOKEN=test-internal-token NUXT_SESSION_SECRET=test-session-secret npm run build && env NUXT_CONTROL_PLANE_URL=http://127.0.0.1:18081 NUXT_CONTROL_PLANE_TOKEN=test-internal-token NUXT_SESSION_SECRET=test-session-secret NUXT_PORT=39329 npm run start',
      url: 'http://127.0.0.1:39329/login',
      reuseExistingServer: false,
      timeout: 180000,
    },
  ],
})
