<script setup lang="ts">
import type { AccountRecordView, SiteRecordView } from '../types/controlPlane'

const api = useControlPlane()
const { t, translateError } = useAppI18n()

type AccountAuthMode = AccountRecordView['auth_mode']

const saveMessage = ref('')
const editingId = ref('')
const cookiesJson = ref('')
const siteFilter = ref('all')
const authFilter = ref<'all' | AccountAuthMode>('all')
const draft = reactive({
  id: '',
  site_id: '',
  display_name: '',
  username: '',
  auth_mode: 'password' as AccountAuthMode,
  password: '',
  api_user: '',
  session_cookies: {} as Record<string, string>,
  enabled: true,
  session_status: 'unknown',
  last_checkin_status: 'pending',
  last_checkin_date: null as string | null,
  last_checkin_at: null as string | null,
  last_quota_awarded: 0,
  total_checkins: 0,
  total_quota_awarded: 0,
  last_error_message: '',
  created_at: '',
  updated_at: '',
})

const [
  { data: sitesResponse, refresh: refreshSites },
  { data: accountsResponse, refresh: refreshAccounts },
] = await Promise.all([
  useAsyncData('account-sites', () => api.listSites()),
  useAsyncData('account-records', () => api.listAccounts()),
])

const sites = computed(() => (sitesResponse.value || []) as SiteRecordView[])
const accounts = computed(() => (accountsResponse.value || []) as AccountRecordView[])
const authModeOptions = computed<Array<{ label: string; value: AccountAuthMode }>>(() => [
  { label: t('密码登录'), value: 'password' },
  { label: t('Cookie 会话'), value: 'cookies' },
  { label: t('GitHub OAuth'), value: 'github_oauth' },
  { label: t('Linux.do OAuth'), value: 'linuxdo_oauth' },
])
const siteOptions = computed(() => {
  return sites.value.map((item) => ({ label: item.name, value: item.id }))
})
const siteFilterOptions = computed(() => [
  { label: t('全部站点'), value: 'all' },
  ...sites.value.map((item) => ({ label: item.name, value: item.id })),
])
const authFilterOptions = computed(() => [
  { label: t('全部认证方式'), value: 'all' },
  ...authModeOptions.value,
])
const accountLabels = computed(() => {
  const enabledCount = accounts.value.filter((item) => item.enabled).length
  const successCount = accounts.value.filter((item) => item.last_checkin_status === 'success').length
  const oauthCount = accounts.value.filter((item) => item.auth_mode === 'github_oauth' || item.auth_mode === 'linuxdo_oauth').length
  return [
    { label: `${t('账号')} ${accounts.value.length}`, state: accounts.value.length ? 'configured' : 'unconfigured' },
    { label: `${t('已启用')} ${enabledCount}`, state: enabledCount ? 'configured' : 'neutral' },
    { label: `${t('最近成功')} ${successCount}`, state: successCount ? 'success' : 'neutral' },
    { label: `${t('OAuth 账号 {count}', { count: oauthCount })}`, state: oauthCount ? 'info' : 'neutral' },
  ]
})
const visibleAccounts = computed(() => {
  return accounts.value
    .filter((item) => (siteFilter.value === 'all' ? true : item.site_id === siteFilter.value))
    .filter((item) => (authFilter.value === 'all' ? true : item.auth_mode === authFilter.value))
})
const hasSites = computed(() => sites.value.length > 0)
const refreshAll = async () => {
  await Promise.all([refreshSites(), refreshAccounts()])
}

const resetDraft = () => {
  editingId.value = ''
  cookiesJson.value = ''
  draft.id = ''
  draft.site_id = sites.value[0]?.id || ''
  draft.display_name = ''
  draft.username = ''
  draft.auth_mode = 'password'
  draft.password = ''
  draft.api_user = ''
  draft.session_cookies = {}
  draft.enabled = true
  draft.session_status = 'unknown'
  draft.last_checkin_status = 'pending'
  draft.last_checkin_date = null
  draft.last_checkin_at = null
  draft.last_quota_awarded = 0
  draft.total_checkins = 0
  draft.total_quota_awarded = 0
  draft.last_error_message = ''
  draft.created_at = ''
  draft.updated_at = ''
}

watchEffect(() => {
  if (!draft.site_id && sites.value.length) {
    draft.site_id = sites.value[0].id
  }
})

const editAccount = (account: AccountRecordView) => {
  editingId.value = account.id
  Object.assign(draft, account)
  cookiesJson.value = account.auth_mode === 'cookies' ? JSON.stringify(account.session_cookies || {}, null, 2) : ''
}

const isCookieMode = computed(() => draft.auth_mode === 'cookies')
const parseCookies = () => {
  if (!cookiesJson.value.trim()) {
    throw new Error(t('Cookie 模式必须填写 API 用户和 Cookies JSON'))
  }
  let parsed: unknown
  try {
    parsed = JSON.parse(cookiesJson.value)
  } catch {
    throw new Error(t('JSON 格式不正确'))
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(t('Cookies JSON 必须是对象'))
  }
  const normalized = Object.entries(parsed as Record<string, unknown>).reduce<Record<string, string>>((result, [key, value]) => {
    const normalizedKey = String(key || '').trim()
    const normalizedValue = String(value || '').trim()
    if (normalizedKey && normalizedValue) {
      result[normalizedKey] = normalizedValue
    }
    return result
  }, {})
  if (!Object.keys(normalized).length) {
    throw new Error(t('Cookie 模式必须填写 API 用户和 Cookies JSON'))
  }
  return normalized
}

const saveAccount = async () => {
  saveMessage.value = ''
  try {
    const payload: Record<string, unknown> = {
      site_id: draft.site_id,
      display_name: draft.display_name.trim(),
      username: draft.username.trim(),
      auth_mode: draft.auth_mode,
      password: draft.password.trim(),
      api_user: '',
      session_cookies: {},
      enabled: draft.enabled,
      session_status: draft.session_status,
      last_checkin_status: draft.last_checkin_status,
      last_checkin_date: draft.last_checkin_date,
      last_checkin_at: draft.last_checkin_at,
      last_quota_awarded: draft.last_quota_awarded,
      total_checkins: draft.total_checkins,
      total_quota_awarded: draft.total_quota_awarded,
      last_error_message: draft.last_error_message.trim(),
    }
    if (!payload.site_id || !payload.auth_mode) {
      saveMessage.value = t('认证方式和站点不能为空')
      return
    }
    if (payload.auth_mode === 'cookies') {
      payload.api_user = draft.api_user.trim()
      payload.session_cookies = parseCookies()
      payload.username = `cookie-${payload.api_user}`
      payload.password = ''
      if (!payload.api_user) {
        saveMessage.value = t('Cookie 模式必须填写 API 用户和 Cookies JSON')
        return
      }
    } else {
      payload.api_user = ''
      payload.session_cookies = {}
      if (!payload.username || !payload.password) {
        saveMessage.value = t('密码或 OAuth 模式必须填写用户名和密码')
        return
      }
    }
    if (editingId.value) {
      payload.id = draft.id
      payload.created_at = draft.created_at
      payload.updated_at = draft.updated_at
      await api.updateAccount(editingId.value, payload)
    } else {
      await api.createAccount(payload)
    }
    await refreshAccounts()
    saveMessage.value = t(editingId.value ? '账号已更新' : '账号已创建')
    resetDraft()
  } catch (error: any) {
    saveMessage.value = translateError(error?.data?.message || error?.message, '账号保存失败')
  }
}

const siteName = (siteId: string) => sites.value.find((item) => item.id === siteId)?.name || t('未知站点')
const authModeLabel = (authMode: AccountAuthMode) => {
  if (authMode === 'cookies') {
    return t('Cookie 会话')
  }
  if (authMode === 'github_oauth') {
    return t('GitHub OAuth')
  }
  if (authMode === 'linuxdo_oauth') {
    return t('Linux.do OAuth')
  }
  return t('密码登录')
}
const authModeState = (authMode: AccountAuthMode) => authMode === 'password' ? 'configured' : 'info'
const accountIdentity = (account: AccountRecordView) => {
  if (account.auth_mode === 'cookies') {
    return `${t('API 用户')} / ${account.api_user}`
  }
  return `${t('用户名')} / ${account.username}`
}
const checkinState = (status: AccountRecordView['last_checkin_status']) => {
  if (status === 'success') {
    return 'success'
  }
  if (status === 'failed' || status === 'blocked') {
    return 'failed'
  }
  if (status === 'skipped') {
    return 'disabled'
  }
  return 'neutral'
}
</script>

<template>
  <AppShell>
    <PageHeader
      :title="t('账号')"
      :description="t('管理站点账号、签到状态与累计收益')"
      :eyebrow="t('任务中心')"
    >
      <template #actions>
        <div class="button-row">
          <button class="button button--secondary" @click="refreshAll">{{ t('刷新账号') }}</button>
        </div>
      </template>
    </PageHeader>
    <div class="button-row page-summary-strip">
      <StatusBadge v-for="item in accountLabels" :key="item.label" :label="item.label" :state="item.state" />
    </div>
    <p v-if="saveMessage" class="status-note" aria-live="polite">{{ saveMessage }}</p>
    <div class="panel-grid panel-grid--two">
      <section class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ editingId ? t('编辑账号') : t('新增账号') }}</h2>
          <button class="button button--secondary" @click="resetDraft">{{ t('清空表单') }}</button>
        </div>
        <div class="stack-list">
          <FieldBlock for-id="account-auth-mode" :label="t('认证方式')" :description="t('为每个账号选择密码登录、Cookie 会话或 OAuth 兼容模式')">
            <AppSelect
              id="account-auth-mode"
              :model-value="draft.auth_mode"
              :options="authModeOptions"
              @update:model-value="draft.auth_mode = $event as AccountAuthMode"
            />
          </FieldBlock>
          <FieldBlock for-id="account-site" :label="t('所属站点')" :description="t('每个账号属于一个 new-api 站点')">
            <AppSelect
              id="account-site"
              :model-value="draft.site_id"
              :options="siteOptions"
              :placeholder="t('请先创建站点')"
              :disabled="!hasSites"
              @update:model-value="draft.site_id = String($event || '')"
            />
          </FieldBlock>
          <FieldBlock for-id="account-display-name" :label="t('显示名称')" :description="t('未填写时默认展示用户名')">
            <input id="account-display-name" v-model="draft.display_name" class="input">
          </FieldBlock>
          <FieldBlock
            v-if="!isCookieMode"
            for-id="account-username"
            :label="t('用户名')"
            :description="draft.auth_mode === 'password' ? t('用于调用 new-api 标准登录接口') : t('用于兼容站点的 OAuth 浏览器登录链')"
          >
            <input id="account-username" v-model="draft.username" class="input">
          </FieldBlock>
          <FieldBlock
            v-if="!isCookieMode"
            for-id="account-password"
            :label="t('密码')"
            :description="t('密码账号和 OAuth 兼容账号都会在任务执行时使用这里的凭据')"
          >
            <PasswordField id="account-password" v-model="draft.password" autocomplete="off" />
          </FieldBlock>
          <FieldBlock
            v-if="isCookieMode"
            for-id="account-api-user"
            :label="t('API 用户')"
            :description="t('用于 new-api Cookie 会话复用，对应 New-Api-User')"
          >
            <input id="account-api-user" v-model="draft.api_user" class="input input--code">
          </FieldBlock>
          <FieldBlock
            v-if="isCookieMode"
            for-id="account-cookies"
            :label="t('Cookies JSON')"
            :description="t('填写浏览器会话 Cookies，必须是 JSON 对象')"
          >
            <textarea
              id="account-cookies"
              v-model="cookiesJson"
              class="textarea textarea--code"
              placeholder='{"session":"..."}'
              spellcheck="false"
            />
          </FieldBlock>
          <FieldBlock for-id="account-enabled" :label="t('启用状态')" :description="t('关闭后该账号不进入每日任务')">
            <AppSelect
              id="account-enabled"
              :model-value="draft.enabled"
              :options="[
                { label: t('已启用'), value: true },
                { label: t('已禁用'), value: false },
              ]"
              @update:model-value="draft.enabled = $event as boolean"
            />
          </FieldBlock>
          <FieldBlock for-id="account-last-error" :label="t('最近异常')" :description="t('记录密码失效、验证码或兼容问题')">
            <textarea id="account-last-error" v-model="draft.last_error_message" class="textarea" />
          </FieldBlock>
          <div class="button-row">
            <button class="button button--primary" :disabled="!hasSites" @click="saveAccount">{{ t(editingId ? '保存账号修改' : '创建账号') }}</button>
            <NuxtLink v-if="!hasSites" class="button button--secondary" to="/sites">{{ t('前往站点') }}</NuxtLink>
          </div>
          <p v-if="!hasSites" class="status-note">{{ t('先创建站点后才能录入账号。') }}</p>
        </div>
      </section>
      <section class="card surface-card">
        <div class="section-head">
          <h2 class="card__title">{{ t('账号清单') }}</h2>
          <StatusBadge :label="t('筛选结果 {count}', { count: visibleAccounts.length })" state="info" :dot="false" />
        </div>
        <div class="panel-grid panel-grid--two" style="margin-bottom: 16px;">
          <FieldBlock for-id="account-site-filter" :label="t('站点筛选')" :description="t('只看某个站点下的账号资产')">
            <AppSelect
              id="account-site-filter"
              :model-value="siteFilter"
              :options="siteFilterOptions"
              @update:model-value="siteFilter = String($event || 'all')"
            />
          </FieldBlock>
          <FieldBlock for-id="account-auth-filter" :label="t('认证方式筛选')" :description="t('按密码、Cookie 或 OAuth 方式过滤账号')">
            <AppSelect
              id="account-auth-filter"
              :model-value="authFilter"
              :options="authFilterOptions"
              @update:model-value="authFilter = ($event as typeof authFilter.value)"
            />
          </FieldBlock>
        </div>
        <div v-if="visibleAccounts.length" class="stack-list">
          <article v-for="account in visibleAccounts" :key="account.id" class="subcard">
            <div class="section-head">
              <strong>{{ account.display_name || account.username }}</strong>
              <StatusBadge :label="account.enabled ? t('已启用') : t('已禁用')" :state="account.enabled ? 'configured' : 'disabled'" />
            </div>
            <p class="muted">{{ siteName(account.site_id) }} / {{ accountIdentity(account) }}</p>
            <div class="status-list">
              <StatusBadge :label="`${t('认证方式')} ${authModeLabel(account.auth_mode)}`" :state="authModeState(account.auth_mode)" />
              <StatusBadge :label="`${t('会话状态')} ${t(account.session_status)}`" state="neutral" />
              <StatusBadge :label="`${t('签到状态')} ${t(account.last_checkin_status)}`" :state="checkinState(account.last_checkin_status)" />
              <StatusBadge :label="`${t('累计签到')} ${account.total_checkins}`" state="info" />
              <StatusBadge :label="`${t('累计额度')} ${account.total_quota_awarded}`" state="configured" />
            </div>
            <div class="button-row">
              <button class="button button--secondary" @click="editAccount(account)">{{ t('编辑') }}</button>
            </div>
          </article>
        </div>
        <div v-else-if="accounts.length" class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="accounts" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('当前筛选下没有账号') }}</strong>
            <p class="muted">{{ t('调整站点或认证方式筛选后再查看。') }}</p>
          </div>
        </div>
        <div v-else class="dashboard-empty">
          <span class="dashboard-empty__icon"><AppIcon name="accounts" :size="18" /></span>
          <div class="dashboard-empty__copy">
            <strong>{{ t('暂无账号记录') }}</strong>
            <p class="muted">{{ t('先创建站点，再录入账号。') }}</p>
          </div>
          <div class="button-row dashboard-empty__actions">
            <NuxtLink class="button button--secondary" to="/sites">{{ t('前往站点') }}</NuxtLink>
          </div>
        </div>
      </section>
    </div>
  </AppShell>
</template>
