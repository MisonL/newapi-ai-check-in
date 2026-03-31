<script setup lang="ts">
const route = useRoute()
const { t } = useAppI18n()

const items = [
  { to: '/dashboard', label: '仪表盘' },
  { to: '/main-checkin', label: '主签到' },
  { to: '/aux-jobs', label: '辅助任务' },
  { to: '/schedules', label: '调度计划' },
  { to: '/settings', label: '系统设置' },
]

const logout = async () => {
  await $fetch('/api/auth/logout', { method: 'POST' })
  await navigateTo('/login')
}
</script>

<template>
  <div class="page-shell">
    <aside class="page-shell__sidebar">
      <div class="brand">
        <div class="brand__mark" />
        <div>
          <div>newapi.ai check-in</div>
          <div class="muted">{{ t('控制面') }}</div>
        </div>
      </div>
      <nav class="sidebar-nav">
        <NuxtLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="sidebar-nav__link"
          :class="{ 'sidebar-nav__link--active': route.path === item.to }"
        >
          {{ t(item.label) }}
        </NuxtLink>
      </nav>
    </aside>
    <div class="page-shell__content">
      <header class="topbar">
        <div>
          <strong>{{ t(items.find((item) => item.to === route.path)?.label || '控制台') }}</strong>
        </div>
        <div class="button-row">
          <LocaleToggle />
          <ThemeToggle />
          <button class="button button--danger" @click="logout">{{ t('退出登录') }}</button>
        </div>
      </header>
      <main class="content-wrap">
        <slot />
      </main>
    </div>
  </div>
</template>
