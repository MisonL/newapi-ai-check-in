<script setup lang="ts">
const { theme, setTheme } = useThemeMode()
const { t, formatTheme } = useAppI18n()
</script>

<template>
  <div class="button-row">
    <button class="button button--secondary" :class="{ 'sidebar-nav__link--active': theme === 'light' }" @click="setTheme('light')">
      {{ t('亮色') }}
    </button>
    <button class="button button--secondary" :class="{ 'sidebar-nav__link--active': theme === 'dark' }" @click="setTheme('dark')">
      {{ t('暗色') }}
    </button>
    <button class="button button--secondary" :class="{ 'sidebar-nav__link--active': theme === 'auto' }" @click="setTheme('auto')">
      {{ formatTheme('auto') }}
    </button>
  </div>
</template>
