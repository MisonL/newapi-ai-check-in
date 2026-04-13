<script setup lang="ts">
import type { AccountRecordView, SiteRecordView } from '../types/controlPlane'

const api = useControlPlane()
const { t, translateError } = useAppI18n()

const saveMessage = ref('')
const editingId = ref('')
const draft = reactive({
  id: '',
  name: '',
  base_url: '',
  enabled: true,
  compatibility_level: 'standard',
  last_probe_status: 'unknown',
  checkin_enabled_detected: null as boolean | null,
  checkin_min_quota_detected: null as number | null,
  checkin_max_quota_detected: null as number | null,
  notes: '',
  created_at: '',
  updated_at: '',
})

const [
  { data: sitesResponse, refresh: refreshSites },
  { data: accountsResponse, refresh: refreshAccounts },
  { data: todayResponse, refresh: refreshToday },
] = await Promise.all([
  useAsyncData('site-records', () => api.listSites()),
  useAsyncData('site-accounts', () => api.listAccounts()),
  useAsyncData('site-today-tasks', () => api.getTaskCenterToday()),
])
const sites = computed(() => (sitesResponse.value || []) as SiteRecordView[])
const accounts = computed(() => (accountsResponse.value || []) as AccountRecordView[])
const todayTasks = computed(() => todayResponse.value?.tasks || [])
const summaryLabels = computed(() => {
  const enabledCount = sites.value.filter((item) => item.enabled).length
  const standardCount = sites.value.filter((item) => item.compatibility_level === 'standard').length
  return [
    { label: `${t('站点')} ${sites.value.length}`, state: sites.value.length ? 'configured' : 'unconfigured' },
    { label: `${t('已启用')} ${enabledCount}`, state: enabledCount ? 'configured' : 'neutral' },
    { label: `${t('标准兼容')} ${standardCount}`, state: standardCount ? 'success' : 'neutral' },
  ]
})
const siteMetrics = computed(() => {
  return sites.value.reduce<Record<string, {
    accountCount: number
    enabledAccountCount: number
    todayTotal: number
    todaySuccess: number
    todayBlocked: number
    todayFailed: number
  }>>((result, site) => {
    const siteAccounts = accounts.value.filter((account) => account.site_id === site.id)
    const siteTodayTasks = todayTasks.value.filter((task) => task.site_id === site.id)
    result[site.id] = {
      accountCount: siteAccounts.length,
      enabledAccountCount: siteAccounts.filter((account) => account.enabled).length,
      todayTotal: siteTodayTasks.length,
      todaySuccess: siteTodayTasks.filter((task) => task.status === 'success' || task.status === 'skipped').length,
      todayBlocked: siteTodayTasks.filter((task) => task.status === 'blocked').length,
      todayFailed: siteTodayTasks.filter((task) => task.status === 'failed').length,
    }
    return result
  }, {})
})
const refreshAll = async () => {
  await Promise.all([refreshSites(), refreshAccounts(), refreshToday()])
}

const resetDraft = () => {
  editingId.value = ''
  draft.id = ''
  draft.name = ''
  draft.base_url = ''
  draft.enabled = true
  draft.compatibility_level = 'standard'
  draft.last_probe_status = 'unknown'
  draft.checkin_enabled_detected = null
  draft.checkin_min_quota_detected = null
  draft.checkin_max_quota_detected = null
  draft.notes = ''
  draft.created_at = ''
  draft.updated_at = ''
}

const editSite = (site: SiteRecordView) => {
  editingId.value = site.id
  Object.assign(draft, site)
}

const saveSite = async () => {
  saveMessage.value = ''
  try {
    const payload: Record<string, unknown> = {
      name: draft.name.trim(),
      base_url: draft.base_url.trim(),
      enabled: draft.enabled,
      compatibility_level: draft.compatibility_level,
      last_probe_status: draft.last_probe_status,
      checkin_enabled_detected: draft.checkin_enabled_detected,
      checkin_min_quota_detected: draft.checkin_min_quota_detected,
      checkin_max_quota_detected: draft.checkin_max_quota_detected,
      notes: draft.notes.trim(),
    }
    if (!payload.name || !payload.base_url) {
      saveMessage.value = t('名称和站点地址不能为空')
      return
    }
    if (editingId.value) {
      payload.id = draft.id
      if (draft.created_at) {
        payload.created_at = draft.created_at
      }
      if (draft.updated_at) {
        payload.updated_at = draft.updated_at
      }
      await api.updateSite(editingId.value, payload)
    } else {
      await api.createSite(payload)
    }
    await refreshSites()
    saveMessage.value = t(editingId.value ? '站点已更新' : '站点已创建')
    resetDraft()
  } catch (error: any) {
    saveMessage.value = translateError(error?.data?.message || error?.message, '站点保存失败')
  }
}
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('站点')"
      :description="t('管理 new-api 站点地址、兼容等级与签到能力探测结果')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--secondary" @click="refreshAll">{{ t('刷新站点') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge v-for="item in summaryLabels" :key="item.label" :label="item.label" :state="item.state" />
    </div>
    <p v-if="saveMessage" class="status-note" aria-live="polite">{{ saveMessage }}</p>
    <div class="panel-grid panel-grid--two">
      <section class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ editingId ? t('编辑站点') : t('新增站点') }}</h2>
          <button class="button button--secondary" @click="resetDraft">{{ t('清空表单') }}</button>
        </div>
        <div class="stack-list">
          <FieldBlock for-id="site-name" :label="t('站点名称')" :description="t('用于任务中心和报表展示')">
            <input id="site-name" v-model="draft.name" class="input">
          </FieldBlock>
          <FieldBlock for-id="site-url" :label="t('站点地址')" :description="t('填写 new-api 根地址，例如 https://example.com')">
            <input id="site-url" v-model="draft.base_url" class="input input--code">
          </FieldBlock>
          <FieldBlock for-id="site-compatibility" :label="t('兼容等级')" :description="t('用于区分标准接口、浏览器兼容和旧链路兼容站点')">
            <AppSelect
              id="site-compatibility"
              :model-value="draft.compatibility_level"
              :options="[
                { label: t('标准兼容'), value: 'standard' },
                { label: t('浏览器回退'), value: 'browser' },
                { label: t('旧链路兼容'), value: 'legacy' },
                { label: t('暂不兼容'), value: 'unsupported' },
              ]"
              @update:model-value="draft.compatibility_level = $event as string"
            />
          </FieldBlock>
          <FieldBlock for-id="site-enabled" :label="t('启用状态')" :description="t('关闭后保留站点记录，但不进入任务调度')">
            <AppSelect
              id="site-enabled"
              :model-value="draft.enabled"
              :options="[
                { label: t('已启用'), value: true },
                { label: t('已禁用'), value: false },
              ]"
              @update:model-value="draft.enabled = $event as boolean"
            />
          </FieldBlock>
          <FieldBlock for-id="site-notes" :label="t('备注')" :description="t('记录站点差异、运营说明或临时注意事项')">
            <textarea id="site-notes" v-model="draft.notes" class="textarea" />
          </FieldBlock>
          <div class="button-row">
            <button class="button button--primary" @click="saveSite">{{ t(editingId ? '保存站点修改' : '创建站点') }}</button>
          </div>
        </div>
      </section>
      <section class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ t('站点清单') }}</h2>
          <StatusBadge :label="t('真实站点资产')" state="info" :dot="false" />
        </div>
        <div v-if="sites.length" class="stack-list">
          <article v-for="site in sites" :key="site.id" class="subcard">
            <div class="section-head">
              <strong>{{ site.name }}</strong>
              <StatusBadge :label="site.enabled ? t('已启用') : t('已禁用')" :state="site.enabled ? 'configured' : 'disabled'" />
            </div>
            <p class="muted">{{ site.base_url }}</p>
            <div class="status-list">
              <StatusBadge :label="`${t('兼容等级')} ${t(site.compatibility_level)}`" state="info" />
              <StatusBadge :label="`${t('探测状态')} ${t(site.last_probe_status)}`" state="neutral" />
              <StatusBadge :label="t('账号 {count}', { count: siteMetrics[site.id]?.accountCount || 0 })" :state="(siteMetrics[site.id]?.accountCount || 0) > 0 ? 'configured' : 'neutral'" />
              <StatusBadge :label="t('启用账号 {count}', { count: siteMetrics[site.id]?.enabledAccountCount || 0 })" :state="(siteMetrics[site.id]?.enabledAccountCount || 0) > 0 ? 'configured' : 'neutral'" />
              <StatusBadge :label="t('今日完成 {done}/{total}', { done: siteMetrics[site.id]?.todaySuccess || 0, total: siteMetrics[site.id]?.todayTotal || 0 })" :state="(siteMetrics[site.id]?.todaySuccess || 0) > 0 ? 'success' : 'neutral'" />
              <StatusBadge :label="t('今日异常 {count}', { count: (siteMetrics[site.id]?.todayBlocked || 0) + (siteMetrics[site.id]?.todayFailed || 0) })" :state="((siteMetrics[site.id]?.todayBlocked || 0) + (siteMetrics[site.id]?.todayFailed || 0)) > 0 ? 'failed' : 'neutral'" />
              <StatusBadge
                :label="site.checkin_enabled_detected === null ? t('签到能力待探测') : t(site.checkin_enabled_detected ? '签到已开启' : '签到未开启')"
                :state="site.checkin_enabled_detected ? 'success' : 'neutral'"
              />
            </div>
            <div class="button-row">
              <button class="button button--secondary" @click="editSite(site)">{{ t('编辑') }}</button>
            </div>
          </article>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="sites" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('暂无站点记录') }}</strong>
            <p class="muted">{{ t('先创建站点，再录入账号和签到状态。') }}</p>
          </div>
        </div>
      </section>
    </div>
  </AppShell>
</template>
