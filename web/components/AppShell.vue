<script setup lang="ts">
const route = useRoute()
const authState = useAuthState()
const authExpiresAt = useAuthExpiresAt()
const { t } = useAppI18n()

const items = [
  { to: '/dashboard', label: '首页', icon: 'dashboard' },
  { to: '/sites', label: '站点', icon: 'sites' },
  { to: '/accounts', label: '账号', icon: 'accounts' },
  { to: '/today', label: '今日任务', icon: 'jobs' },
  { to: '/reports', label: '历史与报表', icon: 'reports' },
  { to: '/incidents', label: '异常处理', icon: 'incidents' },
  { to: '/settings', label: '系统设置', icon: 'settings' },
]

const advancedItems = [
  { to: '/main-checkin', label: '主链路配置' },
  { to: '/schedules', label: '执行计划' },
  { to: '/aux-jobs', label: '补充任务' },
]

const currentItem = computed(() => {
  return items.find((item) => item.to === route.path) || advancedItems.find((item) => item.to === route.path)
})
const currentLabel = computed(() => t(currentItem.value?.label || '任务中心'))
const navigationOptions = computed(() => {
  return [...items, ...advancedItems].map((item) => ({ label: t(item.label), value: item.to }))
})

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
          <div class="brand__eyebrow">{{ t('任务中心') }}</div>
          <div class="brand__title">newapi.ai check-in</div>
          <div class="brand__subtitle">{{ t('多站点签到系统') }}</div>
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
        <p class="sidebar-summary__label">{{ t('运维与高级') }}</p>
        <div class="legacy-link-list">
          <NuxtLink
            v-for="item in advancedItems"
            :key="item.to"
            :to="item.to"
            class="legacy-link"
            :class="{ 'legacy-link--active': route.path === item.to }"
          >
            {{ t(item.label) }}
          </NuxtLink>
        </div>
      </section>
      <section class="sidebar-summary surface-card">
        <p class="sidebar-summary__label">{{ t('当前页面') }}</p>
        <strong class="sidebar-summary__title">{{ currentLabel }}</strong>
        <p class="sidebar-summary__caption">{{ t('任务中心') }}</p>
      </section>
    </aside>
    <div class="page-shell__content">
      <header class="topbar">
        <div class="topbar__context">
          <span class="topbar__badge">{{ t('任务中心') }}</span>
          <div class="topbar__title-group">
            <strong>{{ currentLabel }}</strong>
            <span class="topbar__caption">{{ t('多站点多账号签到任务中心') }}</span>
          </div>
        </div>
        <div class="page-shell__mobile-nav">
          <AppSelect
            :model-value="route.path"
            :options="navigationOptions"
            :label="t('页面导航')"
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
