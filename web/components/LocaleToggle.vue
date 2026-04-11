<script setup lang="ts">
import type { AppLocale } from '../locales/messages'

const { locale, locales, setLocale, t } = useAppI18n()

const localeLabels: Record<AppLocale, string> = {
  'zh-CN': '中文',
  'en-US': '英文',
}
const localeOptions = computed(() => locales.map((item) => ({
  label: localeLabels[item],
  value: item,
})))
</script>

<template>
  <AppSelect :model-value="locale" :options="localeOptions" label="语言切换" size="sm" @update:model-value="setLocale($event as AppLocale)">
    <template #prefix>
      <AppIcon name="locale" :size="14" />
    </template>
  </AppSelect>
</template>
