<script setup lang="ts">
import type { IncidentRecordView } from '../types/controlPlane'

const api = useControlPlane()
const { locale, t } = useAppI18n()

const showResolved = ref(false)
const siteFilter = ref('all')
const severityFilter = ref<'all' | 'low' | 'medium' | 'high'>('all')

const { data: incidentsResponse, refresh: refreshIncidents } = await useAsyncData(
  'task-center-incidents-real',
  () => api.getTaskCenterIncidents(showResolved.value),
  { watch: [showResolved] }
)

const incidents = computed(() => (incidentsResponse.value || []) as IncidentRecordView[])
const siteOptions = computed(() => {
  const names = [...new Set(incidents.value.map((incident) => incident.site_name))].sort((left, right) => left.localeCompare(right))
  return [
    { label: t('全部站点'), value: 'all' },
    ...names.map((name) => ({ label: name, value: name })),
  ]
})
const severityOptions = computed(() => [
  { label: t('全部严重级别'), value: 'all' },
  { label: t('high'), value: 'high' },
  { label: t('medium'), value: 'medium' },
  { label: t('low'), value: 'low' },
])

const formatDateTime = (value: string | null | undefined) => {
  if (!value) {
    return t('未安排')
  }
  return new Intl.DateTimeFormat(locale.value, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const statusState = (status: IncidentRecordView['status']) => {
  if (status === 'failed' || status === 'blocked') {
    return 'failed'
  }
  if (status === 'success') {
    return 'success'
  }
  if (status === 'skipped') {
    return 'disabled'
  }
  return 'neutral'
}

const severityState = (severity?: IncidentRecordView['severity']) => {
  if (severity === 'high') {
    return 'failed'
  }
  if (severity === 'medium') {
    return 'info'
  }
  return 'neutral'
}

const unresolvedCount = computed(() => incidents.value.filter((item) => !item.resolved).length)
const visibleIncidents = computed(() => {
  return incidents.value
    .filter((incident) => (siteFilter.value === 'all' ? true : incident.site_name === siteFilter.value))
    .filter((incident) => (severityFilter.value === 'all' ? true : (incident.severity || 'medium') === severityFilter.value))
})
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('异常处理')"
      :description="t('聚焦账号级签到异常，直接查看受影响站点、账号、错误原因和最近发生时间')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--secondary" @click="showResolved = !showResolved">
            {{ showResolved ? t('仅看未解决异常') : t('包含已解决异常') }}
          </button>
          <button class="button button--secondary" @click="refreshIncidents()">{{ t('刷新异常') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge :label="t('异常记录 {count}', { count: incidents.length })" :state="incidents.length ? 'failed' : 'configured'" />
      <StatusBadge :label="t('未解决 {count}', { count: unresolvedCount })" :state="unresolvedCount ? 'failed' : 'neutral'" />
      <StatusBadge :label="t(showResolved ? '当前包含已解决异常' : '当前仅显示未解决异常')" state="info" />
    </div>
    <section class="card surface-card">
      <div class="section-head">
        <h2 class="card__title">{{ t('异常列表') }}</h2>
        <StatusBadge :label="t('账号级异常中心')" state="info" :dot="false" />
      </div>
      <div class="panel-grid panel-grid--two" style="margin-bottom: 16px;">
        <FieldBlock for-id="incident-site-filter" :label="t('站点筛选')" :description="t('按站点查看当前聚合的异常记录')">
          <AppSelect
            id="incident-site-filter"
            :model-value="siteFilter"
            :options="siteOptions"
            @update:model-value="siteFilter = String($event || 'all')"
          />
        </FieldBlock>
        <FieldBlock for-id="incident-severity-filter" :label="t('严重级别筛选')" :description="t('优先查看高严重级别异常')">
          <AppSelect
            id="incident-severity-filter"
            :model-value="severityFilter"
            :options="severityOptions"
            @update:model-value="severityFilter = ($event as typeof severityFilter.value)"
          />
        </FieldBlock>
      </div>
      <div v-if="visibleIncidents.length" class="stack-list">
        <article v-for="incident in visibleIncidents" :key="incident.id" class="subcard">
          <div class="section-head">
            <strong>{{ incident.display_name }}</strong>
            <StatusBadge :label="t(incident.status)" :state="statusState(incident.status)" />
          </div>
          <p class="muted">{{ incident.site_name }} / {{ incident.type || t('未知类型') }}</p>
          <div class="status-list">
            <StatusBadge :label="`${t('严重级别')} ${t(incident.severity || 'medium')}`" :state="severityState(incident.severity)" />
            <StatusBadge :label="`${t('最近发生')} ${formatDateTime(incident.last_seen_at || incident.last_checkin_at)}`" state="neutral" />
            <StatusBadge :label="incident.resolved ? t('已解决') : t('待处理')" :state="incident.resolved ? 'configured' : 'failed'" />
          </div>
          <p style="margin: 0;">{{ incident.last_error_message }}</p>
          <p v-if="incident.detail" class="muted">{{ incident.detail }}</p>
        </article>
      </div>
      <div v-else class="dashboard-empty">
        <span class="dashboard-empty__icon"><AppIcon name="incidents" :size="18" /></span>
        <div class="dashboard-empty__copy">
          <strong>{{ t('最近没有异常记录') }}</strong>
          <p class="muted">{{ t('当账号任务进入失败或阻塞状态后，这里会自动聚合并展示。') }}</p>
        </div>
      </div>
    </section>
  </AppShell>
</template>
