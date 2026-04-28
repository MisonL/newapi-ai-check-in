<script setup lang="ts">
type OutcomeItem = {
  id: string
  title: string
  subtitle: string
  status: string
  statusState: string
  quota: number
  detail: string
}

defineProps<{
  items: OutcomeItem[]
  emptyTitle: string
  emptyDescription: string
}>()

const { t } = useAppI18n()
</script>

<template>
  <div class="quick-outcome-list">
    <article v-for="item in items" :key="item.id" class="quick-outcome-row">
      <div class="quick-outcome-row__main">
        <strong>{{ item.title }}</strong>
        <span>{{ item.subtitle }}</span>
      </div>
      <div class="quick-outcome-row__meta">
        <StatusBadge :label="t(item.status)" :state="item.statusState" />
        <span>{{ t('额度 {count}', { count: item.quota }) }}</span>
      </div>
      <p v-if="item.detail" class="quick-outcome-row__detail">{{ item.detail }}</p>
    </article>
    <div v-if="items.length === 0" class="dashboard-empty dashboard-empty--compact">
      <span class="dashboard-empty__icon"><AppIcon name="jobs" :size="18" /></span>
      <div class="dashboard-empty__copy">
        <strong>{{ emptyTitle }}</strong>
        <p class="muted">{{ emptyDescription }}</p>
      </div>
    </div>
  </div>
</template>
