<script setup lang="ts">
const { theme, setTheme } = useThemeMode()
</script>

<template>
  <div class="button-row">
    <button class="button button--secondary" :class="{ 'sidebar-nav__link--active': theme === 'light' }" @click="setTheme('light')">
      Light
    </button>
    <button class="button button--secondary" :class="{ 'sidebar-nav__link--active': theme === 'dark' }" @click="setTheme('dark')">
      Dark
    </button>
    <button class="button button--secondary" :class="{ 'sidebar-nav__link--active': theme === 'auto' }" @click="setTheme('auto')">
      Auto
    </button>
  </div>
</template>
