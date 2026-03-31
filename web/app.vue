<script setup lang="ts">
const { locale } = useAppI18n()

useHead(() => ({
  htmlAttrs: {
    lang: locale.value,
  },
}))
</script>

<template>
  <NuxtPage />
</template>
