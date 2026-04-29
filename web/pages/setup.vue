<script setup lang="ts">
const api = useControlPlane()
const { t, translateRequestError } = useAppI18n()

const refreshBusy = ref(false)
const message = ref('')

const [
  { data: sitesResponse, refresh: refreshSites },
  { data: accountsResponse, refresh: refreshAccounts },
  { data: todayResponse, refresh: refreshToday },
] = await Promise.all([
  useAsyncData('setup-sites-real', () => api.listSites()),
  useAsyncData('setup-accounts-real', () => api.listAccounts()),
  useAsyncData('setup-today-real', () => api.getTaskCenterToday()),
])

const sites = computed(() => sitesResponse.value || [])
const accounts = computed(() => accountsResponse.value || [])
const enabledSites = computed(() => sites.value.filter((site) => site.enabled).length)
const enabledAccounts = computed(() => accounts.value.filter((account) => account.enabled).length)
const readyForTasks = computed(() => enabledSites.value > 0 && enabledAccounts.value > 0)

const refreshAll = async () => {
  refreshBusy.value = true
  message.value = ''
  try {
    await Promise.all([refreshSites(), refreshAccounts(), refreshToday()])
    message.value = t('接入状态已刷新')
  } catch (error: any) {
    message.value = translateRequestError(error, '接入状态刷新失败')
  } finally {
    refreshBusy.value = false
  }
}
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('接入 new-api 站点和账号')"
      :description="t('先添加站点，再添加账号；接入完成后系统会生成今日签到任务。')"
      :eyebrow="t('接入')"
    >
      <template #actions>
        <button type="button" class="button button--secondary" :disabled="refreshBusy" @click="refreshAll">
          {{ refreshBusy ? t('刷新中') : t('刷新') }}
        </button>
      </template>
    </PageHeader>
    <p v-if="message" class="status-note" aria-live="polite">{{ message }}</p>
    <SetupOnboardingGuide
      :site-count="sites.length"
      :enabled-site-count="enabledSites"
      :account-count="accounts.length"
      :enabled-account-count="enabledAccounts"
      :today-task-count="todayResponse?.total_tasks || 0"
    />
    <section class="setup-flow surface-card">
      <div class="setup-flow__summary">
        <p>{{ t('先添加站点，再添加账号；接入完成后系统会生成今日签到任务。') }}</p>
        <div class="setup-flow__metrics">
          <div>
            <span>{{ t('站点') }}</span>
            <strong>{{ enabledSites }}/{{ sites.length }}</strong>
          </div>
          <div>
            <span>{{ t('账号') }}</span>
            <strong>{{ enabledAccounts }}/{{ accounts.length }}</strong>
          </div>
          <div>
            <span>{{ t('今日任务') }}</span>
            <strong>{{ todayResponse?.total_tasks || 0 }}</strong>
          </div>
        </div>
      </div>
      <div class="setup-flow__steps">
        <NuxtLink to="/sites" class="setup-step">
          <span>1</span>
          <strong>{{ t('添加或测试站点') }}</strong>
          <p>{{ t('填写 new-api 地址，确认站点可访问并支持签到接口。') }}</p>
        </NuxtLink>
        <NuxtLink to="/accounts" class="setup-step">
          <span>2</span>
          <strong>{{ t('添加或测试账号') }}</strong>
          <p>{{ t('选择登录方式，优先使用密码登录，必要时再使用 Cookie。') }}</p>
        </NuxtLink>
        <NuxtLink to="/today" class="setup-step" :class="{ 'setup-step--disabled': !readyForTasks }">
          <span>3</span>
          <strong>{{ t('生成并执行今日任务') }}</strong>
          <p>{{ t('接入完成后进入今日任务页，执行今天所有启用账号的签到。') }}</p>
        </NuxtLink>
      </div>
    </section>
  </AppShell>
</template>
