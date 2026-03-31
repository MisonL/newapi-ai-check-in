<script setup lang="ts">
const route = useRoute()

const items = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/main-checkin', label: 'Main Check-in' },
  { to: '/aux-jobs', label: 'Aux Jobs' },
  { to: '/schedules', label: 'Schedules' },
  { to: '/settings', label: 'Settings' }
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
          <div class="muted">Control plane</div>
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
          {{ item.label }}
        </NuxtLink>
      </nav>
    </aside>
    <div class="page-shell__content">
      <header class="topbar">
        <div>
          <strong>{{ items.find((item) => item.to === route.path)?.label || 'Console' }}</strong>
        </div>
        <div class="button-row">
          <ThemeToggle />
          <button class="button button--danger" @click="logout">Logout</button>
        </div>
      </header>
      <main class="content-wrap">
        <slot />
      </main>
    </div>
  </div>
</template>
