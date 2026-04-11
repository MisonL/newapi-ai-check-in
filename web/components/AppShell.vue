<script setup lang="ts">
const route = useRoute()
const authState = useAuthState()
const authExpiresAt = useAuthExpiresAt()
const { t } = useAppI18n()

const items = [
  { to: '/dashboard', label: '仪表盘', icon: 'dashboard' },
  { to: '/main-checkin', label: '主签到', icon: 'checkin' },
  { to: '/aux-jobs', label: '辅助任务', icon: 'jobs' },
  { to: '/schedules', label: '调度计划', icon: 'schedules' },
  { to: '/settings', label: '系统设置', icon: 'settings' },
]

const currentItem = computed(() => items.find((item) => item.to === route.path))
const currentLabel = computed(() => t(currentItem.value?.label || '控制台'))
const navigationOptions = computed(() => items.map((item) => ({ label: item.label, value: item.to })))

const navigate = async (value: string | number | boolean | null) => {
  if (typeof value !== 'string' || value === route.path) {
    return
  }
  await navigateTo(value)
}

const logout = async () => {
  await $fetch('/api/auth/logout', { method: 'POST' })
  authState.value = false
  authExpiresAt.value = null
  await navigateTo('/login')
}
</script>

<template>
  <a class="skip-link" href="#main-content">{{ t('跳到主要内容') }}</a>
  <div class="page-shell">
    <aside class="page-shell__sidebar">
      <div class="brand brand--panel">
        <div class="brand__mark" />
        <div class="brand__copy">
          <div class="brand__eyebrow">{{ t('控制面') }}</div>
          <div class="brand__title">newapi.ai check-in</div>
          <div class="brand__subtitle">{{ t('运维控制台') }}</div>
        </div>
      </div>
      <nav class="sidebar-nav" :aria-label="t('主导航')">
        <NuxtLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="sidebar-nav__link"
          :class="{ 'sidebar-nav__link--active': route.path === item.to }"
        >
          <span class="sidebar-nav__icon">
            <AppIcon :name="item.icon" />
          </span>
          <span class="sidebar-nav__text">
            <strong>{{ t(item.label) }}</strong>
          </span>
        </NuxtLink>
      </nav>
      <section class="sidebar-summary surface-card">
        <p class="sidebar-summary__label">{{ t('当前页面') }}</p>
        <strong class="sidebar-summary__title">{{ currentLabel }}</strong>
        <p class="sidebar-summary__caption">newapi.ai check-in</p>
      </section>
    </aside>
    <div class="page-shell__content">
      <header class="topbar">
        <div class="topbar__context">
          <span class="topbar__badge">{{ t('控制面') }}</span>
          <div class="topbar__title-group">
            <strong>{{ currentLabel }}</strong>
            <span class="topbar__caption">newapi.ai check-in</span>
          </div>
        </div>
        <div class="page-shell__mobile-nav">
          <AppSelect
            :model-value="route.path"
            :options="navigationOptions"
            label="页面导航"
            @update:model-value="navigate"
          />
        </div>
        <div class="topbar__actions">
          <div class="topbar__utility surface-card">
            <LocaleToggle />
            <ThemeToggle />
          </div>
          <button class="button button--ghost button--danger-outline" :aria-label="t('退出登录')" @click="logout">
            <AppIcon name="logout" />
            <span>{{ t('退出登录') }}</span>
          </button>
        </div>
      </header>
      <main id="main-content" class="content-wrap">
        <slot />
      </main>
    </div>
  </div>
</template>
