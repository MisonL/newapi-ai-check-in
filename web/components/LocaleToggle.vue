<script setup lang="ts">
import type { AppLocale } from '../locales/messages'

const { locale, locales, setLocale, t } = useAppI18n()

const localeLabels: Record<AppLocale, string> = {
  'zh-CN': '中文',
  'en-US': '英文',
}
</script>

<template>
  <div class="button-row">
    <button
      v-for="item in locales"
      :key="item"
      class="button button--secondary"
      :class="{ 'sidebar-nav__link--active': locale === item }"
      @click="setLocale(item)"
    >
      {{ t(localeLabels[item]) }}
    </button>
  </div>
</template>
