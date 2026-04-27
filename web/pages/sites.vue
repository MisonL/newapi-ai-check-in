<script setup lang="ts">
import type { AccountRecordView, SiteRecordView } from '../types/controlPlane'

const api = useControlPlane()
const { t, translateRequestError } = useAppI18n()

const saveMessage = ref('')
const refreshBusy = ref(false)
const probeBusy = ref<Record<string, boolean>>({})
const editingId = ref('')
const editorSection = ref<HTMLElement | null>(null)
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
  saveMessage.value = ''
  refreshBusy.value = true
  try {
    await Promise.all([refreshSites(), refreshAccounts(), refreshToday()])
    saveMessage.value = t('站点已刷新')
  } catch (error: any) {
    saveMessage.value = translateRequestError(error, '站点刷新失败')
  } finally {
    refreshBusy.value = false
  }
}

const probeState = (status: SiteRecordView['last_probe_status']) => {
  if (status === 'healthy') {
    return 'success'
  }
  if (status === 'unreachable' || status === 'unsupported') {
    return 'failed'
  }
  if (status === 'degraded') {
    return 'queued'
  }
  return 'neutral'
}

const probeSite = async (site: SiteRecordView) => {
  saveMessage.value = ''
  probeBusy.value = { ...probeBusy.value, [site.id]: true }
  try {
    const result = await api.probeTaskCenterSite(site.id)
    await Promise.all([refreshSites(), refreshToday()])
    if (result.status === 'unreachable') {
      saveMessage.value = t('站点不可达：{message}', {
        message: result.message || result.error_code || site.base_url,
      })
      return
    }
    if (result.status === 'unsupported') {
      saveMessage.value = t('站点探测完成：响应不符合 new-api 签到接口')
      return
    }
    saveMessage.value = t('站点探测完成：{status}', { status: t(result.status) })
  } catch (error: any) {
    saveMessage.value = translateRequestError(error, '站点探测失败')
  } finally {
    probeBusy.value = { ...probeBusy.value, [site.id]: false }
  }
}

const deleteSite = async (site: SiteRecordView) => {
  saveMessage.value = ''
  try {
    const result = await api.deleteSite(site.id)
    await Promise.all([refreshSites(), refreshAccounts(), refreshToday()])
    if (editingId.value === site.id) {
      resetDraft(false)
    }
    saveMessage.value = t(
      '站点已删除，已同步清理 {accounts} 个账号、{tasks} 个任务、{incidents} 条异常',
      {
        accounts: result.accounts_deleted || 0,
        tasks: result.daily_tasks_deleted,
        incidents: result.incidents_deleted,
      },
    )
  } catch (error: any) {
    saveMessage.value = translateRequestError(error, '站点删除失败')
  }
}

const resetDraft = (clearMessage = true) => {
  if (clearMessage) {
    saveMessage.value = ''
  }
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
  saveMessage.value = t('正在编辑站点 {name}', { name: site.name })
  nextTick(() => {
    editorSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    document.getElementById('site-name')?.focus({ preventScroll: true })
  })
}

const saveSite = async () => {
  saveMessage.value = ''
  try {
    const originalBaseUrl = draft.base_url.trim()
    const payload: Record<string, unknown> = {
      name: draft.name.trim(),
      base_url: originalBaseUrl,
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
      const site = await api.updateSite(editingId.value, payload)
      saveMessage.value = site.base_url === originalBaseUrl
        ? t('站点已更新')
        : t('站点已更新，站点地址已归一化为 {value}', { value: site.base_url })
    } else {
      const site = await api.createSite(payload)
      saveMessage.value = site.base_url === originalBaseUrl
        ? t('站点已创建')
        : t('站点已创建，站点地址已归一化为 {value}', { value: site.base_url })
    }
    await refreshSites()
    resetDraft(false)
  } catch (error: any) {
    saveMessage.value = translateRequestError(error, '站点保存失败')
  }
}
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('站点')"
      :description="t('管理 new-api 站点地址、兼容等级与今日任务表现')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button type="button" class="button button--secondary" :disabled="refreshBusy" @click="refreshAll">
            {{ refreshBusy ? t('刷新中') : t('刷新站点') }}
          </button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge v-for="item in summaryLabels" :key="item.label" :label="item.label" :state="item.state" />
    </div>
    <p v-if="saveMessage" class="status-note" aria-live="polite">{{ saveMessage }}</p>
    <div class="panel-grid panel-grid--two">
      <section ref="editorSection" class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ editingId ? t('编辑站点') : t('新增站点') }}</h2>
          <button type="button" class="button button--secondary" @click="resetDraft">{{ t('清空表单') }}</button>
        </div>
        <div class="stack-list">
          <FieldBlock for-id="site-name" :label="t('站点名称')" :description="t('用于任务中心和报表展示')">
            <input id="site-name" v-model="draft.name" class="input">
          </FieldBlock>
          <FieldBlock for-id="site-url" :label="t('站点地址')" :description="t('填写 new-api 根地址，例如 https://example.com；也可以直接粘贴 /api/user/checkin 或 /api/user/login 链接')">
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
            <button type="button" class="button button--primary" @click="saveSite">{{ t(editingId ? '保存站点修改' : '创建站点') }}</button>
          </div>
        </div>
      </section>
      <section class="card surface-card asset-list-card">
        <div class="section-head">
          <h2 class="card__title">{{ t('站点清单') }}</h2>
          <StatusBadge :label="t('真实站点资产')" state="info" :dot="false" />
        </div>
        <div v-if="sites.length" class="asset-list">
          <article v-for="site in sites" :key="site.id" class="asset-row">
            <div class="asset-row__title">
              <strong>{{ site.name }}</strong>
              <p class="muted">{{ site.base_url }}</p>
            </div>
            <div class="asset-row__stats">
              <StatusBadge :label="site.enabled ? t('已启用') : t('已禁用')" :state="site.enabled ? 'configured' : 'disabled'" />
              <StatusBadge :label="`${t('兼容等级')} ${t(site.compatibility_level)}`" state="info" />
              <StatusBadge :label="`${t('探测状态')} ${t(site.last_probe_status)}`" :state="probeState(site.last_probe_status)" />
              <StatusBadge
                v-if="site.checkin_enabled_detected !== null"
                :label="site.checkin_enabled_detected ? t('签到接口已启用') : t('签到接口未启用')"
                :state="site.checkin_enabled_detected ? 'success' : 'failed'"
              />
              <StatusBadge
                v-if="site.checkin_min_quota_detected !== null || site.checkin_max_quota_detected !== null"
                :label="t('奖励 {min}-{max}', { min: site.checkin_min_quota_detected ?? '-', max: site.checkin_max_quota_detected ?? '-' })"
                state="info"
              />
              <StatusBadge :label="t('账号 {count}', { count: siteMetrics[site.id]?.accountCount || 0 })" :state="(siteMetrics[site.id]?.accountCount || 0) > 0 ? 'configured' : 'neutral'" />
              <StatusBadge :label="t('启用账号 {count}', { count: siteMetrics[site.id]?.enabledAccountCount || 0 })" :state="(siteMetrics[site.id]?.enabledAccountCount || 0) > 0 ? 'configured' : 'neutral'" />
              <StatusBadge :label="t('今日完成 {done}/{total}', { done: siteMetrics[site.id]?.todaySuccess || 0, total: siteMetrics[site.id]?.todayTotal || 0 })" :state="(siteMetrics[site.id]?.todaySuccess || 0) > 0 ? 'success' : 'neutral'" />
              <StatusBadge :label="t('今日异常 {count}', { count: (siteMetrics[site.id]?.todayBlocked || 0) + (siteMetrics[site.id]?.todayFailed || 0) })" :state="((siteMetrics[site.id]?.todayBlocked || 0) + (siteMetrics[site.id]?.todayFailed || 0)) > 0 ? 'failed' : 'neutral'" />
            </div>
            <div class="asset-row__actions">
              <button type="button" class="button button--secondary" :disabled="probeBusy[site.id]" @click="probeSite(site)">
                {{ probeBusy[site.id] ? t('探测中') : t('探测站点') }}
              </button>
              <button type="button" class="button button--secondary" @click="editSite(site)">{{ t('编辑') }}</button>
              <ConfirmButton
                :label="t('删除站点')"
                :confirm-label="t('确认删除站点')"
                @confirm="deleteSite(site)"
              />
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
