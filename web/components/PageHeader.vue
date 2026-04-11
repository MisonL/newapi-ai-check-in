<script setup lang="ts">
const props = defineProps<{
  title: string
  description: string
  eyebrow?: string
}>()

const { t } = useAppI18n()
</script>

<template>
  <section class="page-header surface-card">
    <div class="page-header__copy">
      <div v-if="props.eyebrow" class="page-header__eyebrow-row">
        <p class="page-header__eyebrow">{{ t(props.eyebrow) }}</p>
      </div>
      <h1 class="page-header__title">{{ t(props.title) }}</h1>
      <p class="page-header__description">{{ t(props.description) }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </section>
</template>
