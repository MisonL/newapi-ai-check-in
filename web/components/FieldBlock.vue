<script setup lang="ts">
const props = defineProps<{
  forId: string
  label: string
  description?: string
}>()

const { t } = useAppI18n()
</script>

<template>
  <div class="field field-block">
    <div class="field-block__head">
      <label class="field__label" :for="props.forId">{{ t(props.label) }}</label>
      <p v-if="props.description" class="field-block__description">{{ t(props.description) }}</p>
    </div>
    <slot />
  </div>
</template>
