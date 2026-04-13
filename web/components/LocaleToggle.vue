<script setup lang="ts">
import type { AppLocale } from '../locales/messages'

const { locale, locales, setLocale, t } = useAppI18n()

const localeOptions = computed(() => locales.map((item) => ({
  label: t(item === 'zh-CN' ? '中文' : '英文'),
  value: item,
})))
</script>

<template>
  <AppSelect :model-value="locale" :options="localeOptions" :label="t('语言切换')" size="sm" @update:model-value="setLocale($event as AppLocale)">
    <template #prefix>
      <AppIcon name="locale" :size="14" />
    </template>
  </AppSelect>
</template>
