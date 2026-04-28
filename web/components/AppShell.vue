<script setup lang="ts">
const route = useRoute()
const authState = useAuthState()
const authExpiresAt = useAuthExpiresAt()
const { t } = useAppI18n()

const items = [
  { to: '/dashboard', label: '首页', icon: 'dashboard', group: 'daily' },
  { to: '/setup', label: '接入', icon: 'sites', group: 'daily' },
  { to: '/today', label: '今日任务', icon: 'jobs', group: 'daily' },
  { to: '/incidents', label: '异常', icon: 'incidents', group: 'daily' },
  { to: '/reports', label: '报表', icon: 'reports', group: 'daily' },
  { to: '/settings', label: '系统设置', icon: 'settings', group: 'advanced' },
]

const assetItems = [
  { to: '/sites', label: '站点清单', icon: 'sites' },
  { to: '/accounts', label: '账号清单', icon: 'accounts' },
]

const advancedItems = [
  { to: '/main-checkin', label: '主链路配置', icon: 'checkin' },
  { to: '/schedules', label: '执行计划', icon: 'schedules' },
  { to: '/aux-jobs', label: '补充任务', icon: 'jobs' },
]

const currentItem = computed(() => {
  return items.find((item) => item.to === route.path)
    || assetItems.find((item) => item.to === route.path)
    || advancedItems.find((item) => item.to === route.path)
})
const currentLabel = computed(() => t(currentItem.value?.label || '任务中心'))
const navigationOptions = computed(() => {
  return [...items, ...assetItems, ...advancedItems].map((item) => ({ label: t(item.label), value: item.to }))
})
const navigationGroups = computed(() => [
  { key: 'daily', label: t('日常使用'), items: items.filter((item) => item.group === 'daily') },
  { key: 'advanced', label: t('系统管理'), items: items.filter((item) => item.group === 'advanced') },
])

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
  <div class="app-console-shell">
    <header class="global-topbar">
      <div class="global-topbar__brand">
        <span class="global-topbar__mark" />
        <strong>newapi.ai check-in</strong>
      </div>
      <nav class="global-topbar__nav" :aria-label="t('主导航')">
        <NuxtLink to="/dashboard" class="global-topbar__link" :class="{ 'global-topbar__link--active': route.path === '/dashboard' }">{{ t('首页') }}</NuxtLink>
        <NuxtLink to="/setup" class="global-topbar__link" :class="{ 'global-topbar__link--active': route.path === '/setup' }">{{ t('接入') }}</NuxtLink>
        <NuxtLink to="/today" class="global-topbar__link" :class="{ 'global-topbar__link--active': route.path === '/today' }">{{ t('今日任务') }}</NuxtLink>
        <NuxtLink to="/incidents" class="global-topbar__link" :class="{ 'global-topbar__link--active': route.path === '/incidents' }">{{ t('异常') }}</NuxtLink>
        <NuxtLink to="/reports" class="global-topbar__link" :class="{ 'global-topbar__link--active': route.path === '/reports' }">{{ t('报表') }}</NuxtLink>
      </nav>
      <div class="global-topbar__actions">
        <LocaleToggle />
        <ThemeToggle />
        <button type="button" class="button button--ghost button--danger-outline" :aria-label="t('退出登录')" @click="logout">
          <AppIcon name="logout" />
          <span>{{ t('退出登录') }}</span>
        </button>
      </div>
    </header>
    <div class="page-shell">
      <aside class="page-shell__sidebar page-shell__sidebar--compact">
        <nav class="sidebar-nav sidebar-nav--compact" :aria-label="t('主导航')">
          <section v-for="group in navigationGroups" :key="group.key" class="sidebar-nav__group">
            <p class="sidebar-nav__section">{{ group.label }}</p>
            <NuxtLink
              v-for="item in group.items"
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
          </section>
        </nav>
        <section class="sidebar-summary surface-card">
          <p class="sidebar-summary__label">{{ t('高级配置') }}</p>
          <p class="sidebar-summary__caption">{{ t('仅首次接入、调度调优或排障时使用') }}</p>
          <div class="legacy-link-list">
            <NuxtLink
              v-for="item in assetItems"
              :key="item.to"
              :to="item.to"
              class="legacy-link"
              :class="{ 'legacy-link--active': route.path === item.to }"
            >
              <span class="legacy-link__icon"><AppIcon :name="item.icon" :size="14" /></span>
              {{ t(item.label) }}
            </NuxtLink>
            <NuxtLink
              v-for="item in advancedItems"
              :key="item.to"
              :to="item.to"
              class="legacy-link"
              :class="{ 'legacy-link--active': route.path === item.to }"
            >
              <span class="legacy-link__icon"><AppIcon :name="item.icon" :size="14" /></span>
              {{ t(item.label) }}
            </NuxtLink>
          </div>
        </section>
      </aside>
      <div class="page-shell__content">
        <header class="topbar topbar--compact">
          <div class="topbar__context">
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
        </header>
        <main id="main-content" class="content-wrap">
          <slot />
        </main>
      </div>
    </div>
  </div>
</template>
