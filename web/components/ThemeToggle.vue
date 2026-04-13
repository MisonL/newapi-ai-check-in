<script setup lang="ts">
const { theme, setTheme } = useThemeMode()
const { t } = useAppI18n()

const themeOptions = computed(() => [
  { label: t('亮色'), value: 'light' },
  { label: t('暗色'), value: 'dark' },
  { label: t('跟随系统'), value: 'auto' },
])
</script>

<template>
  <AppSelect
    :model-value="theme"
    :options="themeOptions"
    :label="t('主题切换')"
    size="sm"
    @update:model-value="setTheme($event as 'light' | 'dark' | 'auto')"
  >
    <template #prefix>
      <AppIcon :name="theme === 'light' ? 'light' : theme === 'dark' ? 'dark' : 'auto'" :size="14" />
    </template>
  </AppSelect>
</template>
