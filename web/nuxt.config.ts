export default defineNuxtConfig({
  ssr: true,
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    controlPlaneUrl: process.env.CONTROL_PLANE_BASE_URL || 'http://127.0.0.1:18080',
    controlPlaneToken: process.env.CONTROL_PLANE_INTERNAL_TOKEN || 'change-me',
    adminPassword: process.env.CONTROL_PLANE_ADMIN_PASSWORD || 'admin123',
    sessionSecret: process.env.CONTROL_PLANE_SESSION_SECRET || 'replace-this-secret',
    public: {}
  },
  routeRules: {
    '/api/**': { cors: false }
  },
  compatibilityDate: '2025-03-30'
})
