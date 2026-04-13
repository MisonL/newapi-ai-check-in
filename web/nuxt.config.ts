export default defineNuxtConfig({
  ssr: true,
  devtools: { enabled: false },
  css: [
    '~/assets/css/main.css',
    '~/assets/css/control-plane.css',
    '~/assets/css/control-plane-layout.css',
    '~/assets/css/control-plane-detail.css',
    '~/assets/css/control-plane-primitives.css',
    '~/assets/css/control-plane-refresh.css',
    '~/assets/css/control-plane-refresh-pages.css',
    '~/assets/css/control-plane-enhancements.css',
  ],
  runtimeConfig: {
    controlPlaneUrl: 'http://127.0.0.1:18080',
    controlPlaneToken: '',
    sessionSecret: '',
    sessionMaxAgeSeconds: 60 * 60 * 12,
    public: {
      appTimezone: 'Asia/Shanghai',
    },
  },
  routeRules: {
    '/api/**': { cors: false }
  },
  compatibilityDate: '2025-03-30'
})
