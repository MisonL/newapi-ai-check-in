<script setup lang="ts">
type ActionResultState = 'changed' | 'unchanged' | 'failed'

defineProps<{
  title: string
  subtitle: string
  state: ActionResultState
  stateLabel: string
  items: Array<{ label: string, value: string }>
  details: string[]
}>()
</script>

<template>
  <section class="action-result-panel" :class="`action-result-panel--${state}`" data-testid="today-action-result">
    <div class="action-result-panel__head">
      <div>
        <p class="action-result-panel__eyebrow">{{ stateLabel }}</p>
        <h2 class="action-result-panel__title">{{ title }}</h2>
        <p class="action-result-panel__subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div class="action-result-panel__items">
      <div v-for="item in items" :key="item.label" class="action-result-panel__item">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>
    <ul class="action-result-panel__details">
      <li v-for="detail in details" :key="detail">{{ detail }}</li>
    </ul>
  </section>
</template>
